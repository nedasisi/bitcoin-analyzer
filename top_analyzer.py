"""
Module d'analyse des tops (sommets) du Bitcoin
Miroir du bottom_analyzer mais pour détecter les pics
"""

import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

class TopAnalyzer:
    """
    Classe pour détecter et analyser les tops (sommets) du Bitcoin
    """
    
    def __init__(self, df):
        self.df = df.copy()
        self.tops = pd.DataFrame()
        self.add_indicators()
    
    def add_indicators(self):
        """Ajoute les indicateurs techniques nécessaires"""
        # RSI
        if 'rsi' not in self.df.columns:
            rsi = RSIIndicator(close=self.df['close'], window=14)
            self.df['rsi'] = rsi.rsi()
        
        # Bollinger Bands
        if 'bb_high' not in self.df.columns:
            bb = BollingerBands(close=self.df['close'], window=20, window_dev=2)
            self.df['bb_high'] = bb.bollinger_hband()
            self.df['bb_mid'] = bb.bollinger_mavg()
            self.df['bb_low'] = bb.bollinger_lband()
            self.df['bb_width'] = self.df['bb_high'] - self.df['bb_low']
            self.df['bb_pct'] = (self.df['close'] - self.df['bb_low']) / self.df['bb_width']
        
        # Volume ratio
        if 'volume_ratio' not in self.df.columns:
            self.df['volume_ratio'] = self.df['volume'] / self.df['volume'].rolling(20).mean()
        
        # ATR pour volatilité
        if 'atr' not in self.df.columns:
            high_low = self.df['high'] - self.df['low']
            high_close = np.abs(self.df['high'] - self.df['close'].shift())
            low_close = np.abs(self.df['low'] - self.df['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = np.max(ranges, axis=1)
            self.df['atr'] = true_range.rolling(14).mean()
    
    def detect_simple_tops(self, lookback_periods=30):
        """
        Détecte les tops simples (plus haut local)
        
        Args:
            lookback_periods: Nombre de périodes pour définir un maximum local
        """
        if len(self.df) < lookback_periods * 2:
            return pd.DataFrame()
        
        # Trouver les maxima locaux
        local_maxs = argrelextrema(
            self.df['high'].values, 
            np.greater_equal, 
            order=lookback_periods
        )[0]
        
        tops = []
        for idx in local_maxs:
            # Vérifier que c'est vraiment le plus haut
            window_start = max(0, idx - lookback_periods)
            window_end = min(len(self.df), idx + lookback_periods)
            window_max = self.df.iloc[window_start:window_end]['high'].max()
            
            if self.df.iloc[idx]['high'] >= window_max:
                # Calculer la chute pour info
                drop_pct = 0
                if idx + lookback_periods < len(self.df):
                    future_low = self.df.iloc[idx:idx+lookback_periods]['low'].min()
                    drop_pct = ((self.df.iloc[idx]['high'] - future_low) / self.df.iloc[idx]['high']) * 100
                
                # Volume ratio
                volume_ratio = self.df.iloc[idx].get('volume_ratio', 1)
                
                # Estimer l'heure exacte du top dans la bougie
                candle_timestamp = self.df.index[idx]
                open_price = self.df.iloc[idx]['open']
                close_price = self.df.iloc[idx]['close']
                high_price = self.df.iloc[idx]['high']
                low_price = self.df.iloc[idx]['low']
                
                # Déterminer la position approximative du high dans la bougie
                if close_price > open_price:
                    # Bougie haussière - high probablement vers la fin
                    exact_time_offset = 0.75
                elif abs(high_price - open_price) < abs(high_price - close_price):
                    # High plus proche de l'open - probablement au début
                    exact_time_offset = 0.25
                else:
                    # High au milieu ou vers la fin
                    exact_time_offset = 0.5
                
                # Calculer la durée de la bougie
                if idx > 0:
                    candle_duration = (self.df.index[idx] - self.df.index[idx-1]).total_seconds()
                else:
                    candle_duration = 3600  # Par défaut 1h
                
                # Estimer l'heure exacte
                exact_time_estimate = candle_timestamp + pd.Timedelta(seconds=candle_duration * exact_time_offset)
                
                tops.append({
                    'price': self.df.iloc[idx]['high'],
                    'volume': self.df.iloc[idx]['volume'],
                    'day_of_week': self.df.index[idx].dayofweek,
                    'hour': self.df.index[idx].hour,
                    'drop_pct': drop_pct,
                    'volume_ratio': volume_ratio,
                    'strength': 1,
                    'timestamp': self.df.index[idx],
                    'exact_time': exact_time_estimate,
                    'candle_open': open_price,
                    'candle_close': close_price,
                    'candle_low': low_price,
                    'rsi': self.df.iloc[idx].get('rsi', None),
                    'bb_pct': self.df.iloc[idx].get('bb_pct', None),
                    'type': 'simple'
                })
        
        if tops:
            df_tops = pd.DataFrame(tops)
            df_tops.set_index('timestamp', inplace=True)
            return df_tops
        return pd.DataFrame()
    
    def detect_confirmed_tops(self, min_drop=5, volume_threshold=1.5, rsi_threshold=70):
        """
        Détecte les tops confirmés avec indicateurs
        
        Args:
            min_drop: Chute minimum en % pour confirmer
            volume_threshold: Seuil de volume (x fois la moyenne)
            rsi_threshold: Seuil RSI pour surachat
        """
        tops = []
        lookback = 30
        
        for i in range(lookback, len(self.df) - 8):
            # Vérifier si c'est un plus haut local
            window = self.df.iloc[i-lookback:i+1]
            current_high = self.df.iloc[i]['high']
            
            if current_high != window['high'].max():
                continue
            
            # Vérifier les conditions de confirmation
            volume_ratio = self.df.iloc[i].get('volume_ratio', 1)
            rsi = self.df.iloc[i].get('rsi', 50)
            bb_pct = self.df.iloc[i].get('bb_pct', 0.5)
            
            # Calculer la chute après
            future_window = self.df.iloc[i:min(i+8, len(self.df))]
            future_low = future_window['low'].min()
            drop_pct = ((current_high - future_low) / current_high) * 100
            
            # Conditions pour un top confirmé
            conditions = [
                drop_pct >= min_drop,  # Chute suffisante
                volume_ratio >= volume_threshold,  # Volume élevé
                rsi >= rsi_threshold or bb_pct >= 0.95  # Surachat RSI ou proche BB haute
            ]
            
            if all(conditions):
                # Estimer l'heure exacte
                candle_timestamp = self.df.index[i]
                open_price = self.df.iloc[i]['open']
                close_price = self.df.iloc[i]['close']
                high_price = current_high
                
                if close_price > open_price:
                    exact_time_offset = 0.75
                elif abs(high_price - open_price) < abs(high_price - close_price):
                    exact_time_offset = 0.25
                else:
                    exact_time_offset = 0.5
                
                if i > 0:
                    candle_duration = (self.df.index[i] - self.df.index[i-1]).total_seconds()
                else:
                    candle_duration = 3600
                
                exact_time_estimate = candle_timestamp + pd.Timedelta(seconds=candle_duration * exact_time_offset)
                
                tops.append({
                    'price': current_high,
                    'volume': self.df.iloc[i]['volume'],
                    'day_of_week': self.df.index[i].dayofweek,
                    'hour': self.df.index[i].hour,
                    'drop_pct': drop_pct,
                    'volume_ratio': volume_ratio,
                    'rsi': rsi,
                    'bb_pct': bb_pct,
                    'strength': 2 if rsi >= 75 else 1.5,
                    'timestamp': self.df.index[i],
                    'exact_time': exact_time_estimate,
                    'type': 'confirmed'
                })
        
        if tops:
            df_tops = pd.DataFrame(tops)
            df_tops.set_index('timestamp', inplace=True)
            return df_tops
        return pd.DataFrame()
    
    def detect_major_tops(self, lookback_days=90):
        """
        Détecte les tops majeurs (sommets de marché significatifs)
        
        Args:
            lookback_days: Jours pour définir un top majeur
        """
        tops = []
        lookback_periods = lookback_days * (24 // 4)  # Convertir en périodes 4h
        
        for i in range(lookback_periods, len(self.df) - 30):
            # Vérifier si c'est le plus haut sur la période
            window = self.df.iloc[max(0, i-lookback_periods):i+1]
            current_high = self.df.iloc[i]['high']
            
            if current_high != window['high'].max():
                continue
            
            # Calculer la montée avant (depuis le plus bas précédent)
            past_low = window['low'].min()
            rise_pct = ((current_high - past_low) / past_low) * 100
            
            # Calculer la chute après
            if i + 30 < len(self.df):
                future_window = self.df.iloc[i:i+30]
                future_low = future_window['low'].min()
                drop_pct = ((current_high - future_low) / current_high) * 100
            else:
                drop_pct = 0
            
            # Seulement si montée > 50% et chute > 20%
            if rise_pct > 50 and drop_pct > 20:
                # Estimer l'heure exacte
                candle_timestamp = self.df.index[i]
                open_price = self.df.iloc[i]['open']
                close_price = self.df.iloc[i]['close']
                
                if close_price > open_price:
                    exact_time_offset = 0.75
                else:
                    exact_time_offset = 0.25
                
                if i > 0:
                    candle_duration = (self.df.index[i] - self.df.index[i-1]).total_seconds()
                else:
                    candle_duration = 3600
                
                exact_time_estimate = candle_timestamp + pd.Timedelta(seconds=candle_duration * exact_time_offset)
                
                tops.append({
                    'price': current_high,
                    'volume': self.df.iloc[i]['volume'],
                    'day_of_week': self.df.index[i].dayofweek,
                    'hour': self.df.index[i].hour,
                    'rise_pct': rise_pct,
                    'drop_pct': drop_pct,
                    'strength': 3,
                    'timestamp': self.df.index[i],
                    'exact_time': exact_time_estimate,
                    'type': 'major'
                })
        
        if tops:
            df_tops = pd.DataFrame(tops)
            df_tops.set_index('timestamp', inplace=True)
            return df_tops
        return pd.DataFrame()
    
    def detect_tops(self, method='all'):
        """
        Détecte tous les types de tops
        
        Args:
            method: 'simple', 'confirmed', 'major', ou 'all'
        """
        all_tops = []
        
        if method in ['simple', 'all']:
            simple_tops = self.detect_simple_tops()
            if not simple_tops.empty:
                all_tops.append(simple_tops)
        
        if method in ['confirmed', 'all']:
            confirmed_tops = self.detect_confirmed_tops()
            if not confirmed_tops.empty:
                all_tops.append(confirmed_tops)
        
        if method in ['major', 'all']:
            major_tops = self.detect_major_tops()
            if not major_tops.empty:
                all_tops.append(major_tops)
        
        if all_tops:
            # Combiner et supprimer les doublons
            combined = pd.concat(all_tops)
            # Garder le top avec la force maximale pour chaque timestamp
            combined = combined.sort_values('strength', ascending=False).groupby(level=0).first()
            # IMPORTANT : Trier par index décroissant pour avoir les plus récents en premier
            self.tops = combined.sort_index(ascending=False)
            return self.tops
        
        return pd.DataFrame()
    
    def analyze_patterns(self):
        """Analyse les patterns temporels des tops"""
        if self.tops.empty:
            return {}
        
        # Patterns par jour
        day_stats = self.tops.groupby('day_of_week').agg({
            'price': 'count',
            'strength': 'mean'
        })
        day_stats.columns = ['count', 'avg_strength']
        day_stats['percentage'] = (day_stats['count'] / day_stats['count'].sum() * 100).round(1)
        
        # Patterns par heure
        hour_stats = self.tops.groupby('hour').agg({
            'price': 'count',
            'strength': 'mean'
        })
        hour_stats.columns = ['count', 'avg_strength']
        hour_stats['percentage'] = (hour_stats['count'] / hour_stats['count'].sum() * 100).round(1)
        hour_stats = hour_stats.reset_index()
        hour_stats['hour'] = hour_stats['hour'].astype(int)  # S'assurer que hour est un entier
        
        # Sessions de trading
        def classify_session(hour):
            if 0 <= hour < 8:
                return 'Asie'
            elif 8 <= hour < 16:
                return 'Europe'
            else:
                return 'US'
        
        self.tops['session'] = self.tops['hour'].apply(classify_session)
        session_stats = self.tops.groupby('session').size().to_frame('count')
        session_stats['percentage'] = (session_stats['count'] / session_stats['count'].sum() * 100).round(1)
        
        # Meilleurs moments
        best_day_idx = day_stats['count'].idxmax() if not day_stats.empty else None
        best_hour_idx = hour_stats['count'].idxmax() if not hour_stats.empty else None
        
        DAYS_FR = {0: 'Lundi', 1: 'Mardi', 2: 'Mercredi', 3: 'Jeudi', 4: 'Vendredi', 5: 'Samedi', 6: 'Dimanche'}
        
        return {
            'day_stats': day_stats.reset_index().assign(day=lambda x: x['day_of_week'].map(DAYS_FR)),
            'hour_stats': hour_stats,  # Déjà reset_index avec hour en int
            'session_stats': session_stats.reset_index(),
            'best_day': DAYS_FR.get(best_day_idx, 'N/A'),
            'best_hour': f"{int(best_hour_idx):02d}:00" if best_hour_idx is not None else 'N/A',
            'total_tops': len(self.tops),
            'major_tops': len(self.tops[self.tops['type'] == 'major']) if 'type' in self.tops.columns else 0
        }
    
    def backtest_short_strategy(self, sell_days=None, hold_periods=7):
        """
        Backtest une stratégie de short basée sur les tops
        
        Args:
            sell_days: Liste des jours pour shorter (0=Lundi, 6=Dimanche)
            hold_periods: Nombre de jours pour tenir la position short
        """
        if self.df.empty or self.tops.empty:
            return {}
        
        trades = []
        
        for idx, top in self.tops.iterrows():
            # Vérifier si c'est un jour de vente
            if sell_days and top['day_of_week'] not in sell_days:
                continue
            
            # Point d'entrée (short)
            entry_idx = self.df.index.get_loc(idx)
            entry_price = top['price']
            
            # Point de sortie
            exit_idx = min(entry_idx + hold_periods, len(self.df) - 1)
            exit_price = self.df.iloc[exit_idx]['close']
            
            # Calcul du profit (inversé car on short)
            profit_pct = ((entry_price - exit_price) / entry_price) * 100
            
            trades.append({
                'entry_date': idx,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'profit_pct': profit_pct,
                'hold_days': exit_idx - entry_idx
            })
        
        if not trades:
            return {}
        
        trades_df = pd.DataFrame(trades)
        
        # Calculer les métriques
        winning_trades = trades_df[trades_df['profit_pct'] > 0]
        losing_trades = trades_df[trades_df['profit_pct'] < 0]
        
        return {
            'total_trades': len(trades_df),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': (len(winning_trades) / len(trades_df) * 100) if len(trades_df) > 0 else 0,
            'avg_profit': trades_df['profit_pct'].mean(),
            'median_profit': trades_df['profit_pct'].median(),
            'max_profit': trades_df['profit_pct'].max(),
            'max_loss': trades_df['profit_pct'].min(),
            'sharpe_ratio': trades_df['profit_pct'].mean() / trades_df['profit_pct'].std() if trades_df['profit_pct'].std() != 0 else 0
        }