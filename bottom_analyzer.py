"""
Module d'analyse des bottoms Bitcoin
"""

import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
from datetime import datetime, timedelta
from config import *

class BottomAnalyzer:
    def __init__(self, df):
        """
        Initialise l'analyseur avec les données
        """
        self.df = df.copy()
        self.bottoms = pd.DataFrame()
        
    def detect_bottoms(self, method='all'):
        """
        Détecte les bottoms selon différentes méthodes
        """
        if method == 'all':
            # Combiner plusieurs méthodes
            simple = self.detect_simple_bottoms()
            confirmed = self.detect_confirmed_bottoms()
            major = self.detect_major_bottoms()
            
            # Fusionner les résultats
            bottoms_list = []
            if not simple.empty:
                bottoms_list.append(simple.assign(type='simple'))
            if not confirmed.empty:
                bottoms_list.append(confirmed.assign(type='confirmed'))
            if not major.empty:
                bottoms_list.append(major.assign(type='major'))
            
            if bottoms_list:
                self.bottoms = pd.concat(bottoms_list).sort_index()
                # Supprimer les doublons basés sur l'index (qui est le timestamp)
                self.bottoms = self.bottoms[~self.bottoms.index.duplicated(keep='first')]
            else:
                self.bottoms = pd.DataFrame()
            
        return self.bottoms
    
    def detect_simple_bottoms(self):
        """
        Détecte les bottoms simples (plus bas local)
        """
        lookback = BOTTOM_PARAMS['lookback_periods']
        
        if len(self.df) < lookback * 2:
            return pd.DataFrame()  # Pas assez de données
        
        # Trouver les minima locaux
        local_mins = argrelextrema(
            self.df['low'].values, 
            np.less_equal, 
            order=lookback
        )[0]
        
        bottoms = []
        for idx in local_mins:
            # Vérifier que c'est vraiment le plus bas
            window_start = max(0, idx - lookback)
            window_end = min(len(self.df), idx + lookback)
            window_min = self.df.iloc[window_start:window_end]['low'].min()
            
            if self.df.iloc[idx]['low'] <= window_min:
                # Calculer le rebond pour info (même si pas requis pour simple)
                bounce_pct = 0
                if idx + lookback < len(self.df):
                    future_high = self.df.iloc[idx:idx+lookback]['high'].max()
                    bounce_pct = ((future_high - self.df.iloc[idx]['low']) / self.df.iloc[idx]['low']) * 100
                
                # Calculer le volume ratio si disponible
                volume_ratio = 1
                if 'volume_ratio' in self.df.columns:
                    volume_ratio = self.df.iloc[idx]['volume_ratio']
                
                # Estimer l'heure exacte du bottom dans la bougie
                # On utilise une approximation basée sur le rapport (low-open)/(close-open)
                candle_timestamp = self.df.index[idx]
                open_price = self.df.iloc[idx]['open']
                close_price = self.df.iloc[idx]['close']
                low_price = self.df.iloc[idx]['low']
                high_price = self.df.iloc[idx]['high']
                
                # Déterminer la position approximative du low dans la bougie
                # Si le close est plus bas que l'open, le low est probablement vers la fin
                # Si le close est plus haut que l'open, le low est probablement vers le début/milieu
                if close_price < open_price:
                    # Bougie baissière - low probablement vers la fin
                    exact_time_offset = 0.75  # 75% de la période
                elif abs(low_price - open_price) < abs(low_price - close_price):
                    # Low plus proche de l'open - probablement au début
                    exact_time_offset = 0.25  # 25% de la période
                else:
                    # Low au milieu ou vers la fin
                    exact_time_offset = 0.5  # 50% de la période
                
                # Calculer la durée de la bougie
                if idx > 0:
                    candle_duration = (self.df.index[idx] - self.df.index[idx-1]).total_seconds()
                else:
                    candle_duration = 3600  # Par défaut 1h
                
                # Estimer l'heure exacte
                exact_time_estimate = candle_timestamp + pd.Timedelta(seconds=candle_duration * exact_time_offset)
                
                bottoms.append({
                    'price': self.df.iloc[idx]['low'],
                    'volume': self.df.iloc[idx]['volume'],
                    'day_of_week': self.df.index[idx].dayofweek,
                    'hour': self.df.index[idx].hour,
                    'bounce_pct': bounce_pct,
                    'volume_ratio': volume_ratio,
                    'strength': 1,
                    'timestamp': self.df.index[idx],
                    'exact_time': exact_time_estimate,  # Heure estimée du minimum
                    'candle_open': open_price,
                    'candle_close': close_price,
                    'candle_high': high_price
                })
        
        if bottoms:
            df_bottoms = pd.DataFrame(bottoms)
            df_bottoms.set_index('timestamp', inplace=True)
            return df_bottoms
        return pd.DataFrame()
    
    def detect_confirmed_bottoms(self):
        """
        Détecte les bottoms confirmés (avec rebond)
        """
        lookback = BOTTOM_PARAMS['lookback_periods']
        min_bounce = BOTTOM_PARAMS['min_bounce_percent']
        volume_threshold = BOTTOM_PARAMS['volume_threshold']
        
        bottoms = []
        
        for i in range(lookback, len(self.df) - lookback):
            current_low = self.df.iloc[i]['low']
            
            # Vérifier si c'est un minimum local
            window_before = self.df.iloc[i-lookback:i]['low'].min()
            window_after = self.df.iloc[i+1:i+lookback+1]['low'].min()
            
            if current_low < window_before and current_low <= window_after:
                # Calculer le rebond
                future_high = self.df.iloc[i:i+lookback]['high'].max()
                bounce_pct = ((future_high - current_low) / current_low) * 100
                
                # Vérifier le volume
                volume_ratio = self.df.iloc[i]['volume_ratio'] if 'volume_ratio' in self.df.columns else 1
                
                # Vérifier RSI si disponible
                rsi_oversold = True
                if 'rsi' in self.df.columns:
                    rsi_oversold = self.df.iloc[i]['rsi'] < BOTTOM_PARAMS['rsi_oversold']
                
                # Confirmer le bottom
                if bounce_pct >= min_bounce and volume_ratio >= volume_threshold:
                    # Estimer l'heure exacte du bottom
                    candle_timestamp = self.df.index[i]
                    open_price = self.df.iloc[i]['open']
                    close_price = self.df.iloc[i]['close']
                    low_price = current_low
                    
                    # Logique d'estimation de l'heure exacte
                    if close_price < open_price:
                        exact_time_offset = 0.75
                    elif abs(low_price - open_price) < abs(low_price - close_price):
                        exact_time_offset = 0.25
                    else:
                        exact_time_offset = 0.5
                    
                    if i > 0:
                        candle_duration = (self.df.index[i] - self.df.index[i-1]).total_seconds()
                    else:
                        candle_duration = 3600
                    
                    exact_time_estimate = candle_timestamp + pd.Timedelta(seconds=candle_duration * exact_time_offset)
                    
                    bottoms.append({
                        'price': current_low,
                        'volume': self.df.iloc[i]['volume'],
                        'day_of_week': self.df.index[i].dayofweek,
                        'hour': self.df.index[i].hour,
                        'bounce_pct': bounce_pct,
                        'volume_ratio': volume_ratio,
                        'rsi': self.df.iloc[i].get('rsi', None),
                        'strength': 2 if rsi_oversold else 1.5,
                        'timestamp': self.df.index[i],
                        'exact_time': exact_time_estimate
                    })
        
        if bottoms:
            df_bottoms = pd.DataFrame(bottoms)
            df_bottoms.set_index('timestamp', inplace=True)
            return df_bottoms
        return pd.DataFrame()
    
    def detect_major_bottoms(self):
        """
        Détecte les bottoms majeurs (plus bas sur longue période)
        """
        major_days = BOTTOM_PARAMS['major_bottom_days']
        # Adapter les périodes selon le timeframe
        timeframe = self.df.index.to_series().diff().median()
        hours_per_period = timeframe.total_seconds() / 3600
        major_periods = int(major_days * 24 / hours_per_period)  # Convertir les jours en périodes
        
        bottoms = []
        
        for i in range(major_periods, len(self.df)):
            current_low = self.df.iloc[i]['low']
            
            # Vérifier si c'est le minimum sur la période
            period_min = self.df.iloc[i-major_periods:i+1]['low'].min()
            
            if current_low == period_min:
                # Calculer la profondeur de la chute
                period_high = self.df.iloc[i-major_periods:i]['high'].max()
                drop_pct = ((period_high - current_low) / period_high) * 100
                
                # Vérifier le rebond futur
                if i + 30 < len(self.df):
                    future_high = self.df.iloc[i:i+30]['high'].max()
                    bounce_pct = ((future_high - current_low) / current_low) * 100
                else:
                    bounce_pct = 0
                
                # Seulement si chute > 20% et rebond > 15%
                if drop_pct > 20 and bounce_pct > 15:
                    # Estimer l'heure exacte du bottom
                    candle_timestamp = self.df.index[i]
                    open_price = self.df.iloc[i]['open']
                    close_price = self.df.iloc[i]['close']
                    low_price = current_low
                    
                    if close_price < open_price:
                        exact_time_offset = 0.75
                    elif abs(low_price - open_price) < abs(low_price - close_price):
                        exact_time_offset = 0.25
                    else:
                        exact_time_offset = 0.5
                    
                    if i > 0:
                        candle_duration = (self.df.index[i] - self.df.index[i-1]).total_seconds()
                    else:
                        candle_duration = 3600
                    
                    exact_time_estimate = candle_timestamp + pd.Timedelta(seconds=candle_duration * exact_time_offset)
                    
                    bottoms.append({
                        'price': current_low,
                        'volume': self.df.iloc[i]['volume'],
                        'day_of_week': self.df.index[i].dayofweek,
                        'hour': self.df.index[i].hour,
                        'drop_pct': drop_pct,
                        'bounce_pct': bounce_pct,
                        'strength': 3,
                        'timestamp': self.df.index[i],
                        'exact_time': exact_time_estimate
                    })
        
        if bottoms:
            df_bottoms = pd.DataFrame(bottoms)
            df_bottoms.set_index('timestamp', inplace=True)
            return df_bottoms
        return pd.DataFrame()
    
    def analyze_patterns(self):
        """
        Analyse les patterns des bottoms
        """
        if self.bottoms.empty:
            return {}
        
        analysis = {
            'total_bottoms': len(self.bottoms),
            'by_day': self.bottoms.groupby('day_of_week').size().to_dict(),
            'by_hour': self.bottoms.groupby('hour').size().to_dict(),
            'by_type': self.bottoms.groupby('type').size().to_dict() if 'type' in self.bottoms.columns else {},
        }
        
        # Statistiques par jour
        day_stats = []
        for day in range(7):
            day_bottoms = self.bottoms[self.bottoms['day_of_week'] == day]
            if not day_bottoms.empty:
                day_stats.append({
                    'day': DAYS_FR[day],
                    'count': len(day_bottoms),
                    'percentage': (len(day_bottoms) / len(self.bottoms)) * 100,
                    'avg_strength': day_bottoms['strength'].mean() if 'strength' in day_bottoms.columns else 0
                })
        
        analysis['day_stats'] = pd.DataFrame(day_stats)
        
        # Sessions de trading
        session_stats = []
        for session, (start_hour, end_hour) in TRADING_SESSIONS.items():
            if end_hour == 24:
                session_bottoms = self.bottoms[(self.bottoms['hour'] >= start_hour) | (self.bottoms['hour'] == 0)]
            else:
                session_bottoms = self.bottoms[(self.bottoms['hour'] >= start_hour) & (self.bottoms['hour'] < end_hour)]
            
            session_stats.append({
                'session': session,
                'count': len(session_bottoms),
                'percentage': (len(session_bottoms) / len(self.bottoms)) * 100
            })
        
        analysis['session_stats'] = pd.DataFrame(session_stats)
        
        # Meilleur jour/heure
        if not self.bottoms.empty:
            best_day = self.bottoms['day_of_week'].value_counts().index[0]
            best_hour = self.bottoms['hour'].value_counts().index[0]
            analysis['best_day'] = DAYS_FR[best_day]
            analysis['best_hour'] = f"{best_hour}:00 UTC"
        
        return analysis
    
    def backtest_strategy(self, buy_days=[0], hold_periods=7):
        """
        Backtest une stratégie d'achat sur certains jours
        """
        results = []
        
        for i in range(len(self.df) - hold_periods * 6):  # 6 périodes de 4h par jour
            current_time = self.df.index[i]
            
            # Vérifier si c'est un jour d'achat
            if current_time.dayofweek in buy_days:
                buy_price = self.df.iloc[i]['close']
                sell_idx = min(i + hold_periods * 6, len(self.df) - 1)
                sell_price = self.df.iloc[sell_idx]['close']
                
                profit_pct = ((sell_price - buy_price) / buy_price) * 100
                
                results.append({
                    'buy_date': current_time,
                    'sell_date': self.df.index[sell_idx],
                    'buy_price': buy_price,
                    'sell_price': sell_price,
                    'profit_pct': profit_pct
                })
        
        if results:
            results_df = pd.DataFrame(results)
            
            return {
                'total_trades': len(results_df),
                'winning_trades': len(results_df[results_df['profit_pct'] > 0]),
                'win_rate': len(results_df[results_df['profit_pct'] > 0]) / len(results_df) * 100,
                'avg_profit': results_df['profit_pct'].mean(),
                'median_profit': results_df['profit_pct'].median(),
                'max_profit': results_df['profit_pct'].max(),
                'max_loss': results_df['profit_pct'].min(),
                'sharpe_ratio': results_df['profit_pct'].mean() / results_df['profit_pct'].std() if results_df['profit_pct'].std() > 0 else 0
            }
        
        return {}