"""
Module d'analyse avancée avec système de scoring
Basé sur les recommandations GPT-5 pour la stratégie "excès 4H"
"""

import pandas as pd
import numpy as np
from ta.volatility import BollingerBands, AverageTrueRange
from ta.momentum import RSIIndicator
from scipy import stats

class AdvancedBottomAnalyzer:
    """
    Analyseur avancé avec système de scoring pour détecter les bottoms
    selon la méthode "excès 4H"
    """
    
    def __init__(self, df):
        self.df = df.copy()
        self.add_advanced_indicators()
        
    def add_advanced_indicators(self):
        """
        Ajoute tous les indicateurs avancés recommandés
        """
        # Bollinger Bands 4H
        bb = BollingerBands(self.df['close'], window=20, window_dev=2)
        self.df['bb_low'] = bb.bollinger_lband()
        self.df['bb_mid'] = bb.bollinger_mavg()
        self.df['bb_high'] = bb.bollinger_hband()
        self.df['band_width'] = self.df['bb_high'] - self.df['bb_low']
        
        # Band Z-score (distance aux bandes en sigma)
        self.df['band_z'] = (self.df['bb_low'] - self.df['close']) / self.df['band_width']
        
        # Volume Z-score
        self.df['vol_z'] = self.zscore(self.df['volume'], window=20)
        
        # ATR Z-score (volatilité anormale)
        atr = AverageTrueRange(self.df['high'], self.df['low'], self.df['close'])
        self.df['atr'] = atr.average_true_range()
        self.df['atr_z'] = self.zscore(self.df['atr'], window=20)
        
        # RSI
        rsi = RSIIndicator(self.df['close'], window=14)
        self.df['rsi'] = rsi.rsi()
        
        # Wick Ratio (mèche basse / corps)
        self.df['wick_ratio'] = self.df.apply(self.calculate_wick_ratio, axis=1)
        
        # Divergence RSI
        self.df['rsi_divergence'] = self.detect_rsi_divergence()
        
        # Niveaux psychologiques
        self.df['psycho_level'] = self.df['low'].apply(self.is_psycho_level)
        
        # Plus bas local
        self.df['is_local_low_30'] = self.is_local_low(30)
        self.df['is_local_low_90'] = self.is_local_low(90)
        
        return self.df
    
    def zscore(self, series, window=20):
        """Calcule le Z-score"""
        mean = series.rolling(window).mean()
        std = series.rolling(window).std()
        return (series - mean) / std
    
    def calculate_wick_ratio(self, row):
        """Calcule le ratio mèche/corps"""
        body = abs(row['close'] - row['open'])
        if row['close'] >= row['open']:
            # Bougie verte
            wick = row['open'] - row['low']
        else:
            # Bougie rouge
            wick = row['close'] - row['low']
        
        if body == 0:
            return 0 if wick == 0 else 10  # Grande mèche sans corps
        return wick / body
    
    def detect_rsi_divergence(self, lookback=10):
        """
        Détecte les divergences RSI (prix fait un plus bas, RSI ne suit pas)
        """
        divergence = []
        for i in range(len(self.df)):
            if i < lookback:
                divergence.append(False)
                continue
            
            # Prix actuel vs prix passé
            current_low = self.df['low'].iloc[i]
            past_lows = self.df['low'].iloc[i-lookback:i]
            
            # RSI actuel vs RSI passé
            current_rsi = self.df['rsi'].iloc[i]
            past_rsi = self.df['rsi'].iloc[i-lookback:i]
            
            # Divergence haussière : prix plus bas, RSI plus haut
            is_divergence = (
                current_low < past_lows.min() and 
                current_rsi > past_rsi.min() + 2  # RSI supérieur d'au moins 2 points
            )
            
            divergence.append(is_divergence)
        
        return divergence
    
    def is_psycho_level(self, price, threshold=100):
        """
        Vérifie si le prix touche un niveau psychologique
        (nombre rond : 100k, 105k, 110k, etc.)
        """
        round_level = round(price / 1000) * 1000
        distance = abs(price - round_level)
        return distance < threshold
    
    def is_local_low(self, window):
        """Identifie les plus bas locaux sur une fenêtre donnée"""
        local_lows = []
        for i in range(len(self.df)):
            if i < window:
                local_lows.append(False)
                continue
            
            window_data = self.df['low'].iloc[max(0, i-window):i+1]
            is_min = self.df['low'].iloc[i] == window_data.min()
            local_lows.append(is_min)
        
        return local_lows
    
    def calculate_bottom_score(self, idx):
        """
        Calcule le score d'un bottom (0-10) selon les critères
        """
        score = 0
        row = self.df.iloc[idx]
        
        # 1. Excès Bollinger (band_z)
        if row['band_z'] < -0.10:
            score += 2
        if row['band_z'] < -0.20:
            score += 1  # +3 total si < -0.20
        
        # 2. Volume Z-score
        if row['vol_z'] > 2:
            score += 2
        if row['vol_z'] > 3:
            score += 1  # +3 total si > 3
        
        # 3. Wick ratio (mèche importante)
        if row['wick_ratio'] >= 1.5:
            score += 1
        
        # 4. RSI oversold
        if row['rsi'] < 30:
            score += 1
        
        # 5. Divergence RSI
        if row.get('rsi_divergence', False):
            score += 2
        
        # 6. Plus bas local
        if row.get('is_local_low_30', False):
            score += 1
        if row.get('is_local_low_90', False):
            score += 1  # +2 total si plus bas 90 jours
        
        # 7. Niveau psychologique
        if row.get('psycho_level', False):
            score += 1
        
        return min(score, 10)  # Cap à 10
    
    def detect_bottoms_with_score(self, min_score=6, confirmation_window=8, min_bounce=0.05):
        """
        Détecte les bottoms avec système de scoring
        
        Args:
            min_score: Score minimum requis (0-10)
            confirmation_window: Nombre de bougies pour confirmer
            min_bounce: Rebond minimum requis pour confirmation (5% par défaut)
        """
        bottoms = []
        
        for i in range(30, len(self.df) - confirmation_window):
            # Vérifier si c'est un plus bas local
            if not self.df['is_local_low_30'].iloc[i]:
                continue
            
            # Calculer le score
            score = self.calculate_bottom_score(i)
            
            if score < min_score:
                continue
            
            # Vérifier la confirmation
            entry_price = self.df['close'].iloc[i]
            future_prices = self.df['close'].iloc[i+1:i+1+confirmation_window]
            max_bounce = (future_prices.max() / entry_price - 1)
            
            # Confirmation : soit rebond de min_bounce%, soit retour au-dessus de BB mid
            confirmed = (
                max_bounce >= min_bounce or 
                future_prices.iloc[-1] > self.df['bb_mid'].iloc[i]
            )
            
            if confirmed:
                bottoms.append({
                    'timestamp': self.df.index[i],
                    'score': score,
                    'price': self.df['low'].iloc[i],
                    'close': self.df['close'].iloc[i],
                    'band_z': self.df['band_z'].iloc[i],
                    'vol_z': self.df['vol_z'].iloc[i],
                    'rsi': self.df['rsi'].iloc[i],
                    'wick_ratio': self.df['wick_ratio'].iloc[i],
                    'bounce_pct': max_bounce * 100,
                    'confirmed_in': future_prices.idxmax() - self.df.index[i],
                    'type': self.classify_bottom_type(score)
                })
        
        return pd.DataFrame(bottoms)
    
    def classify_bottom_type(self, score):
        """
        Classifie le type de bottom selon le score
        """
        if score >= 8:
            return 'major'  # Bottom majeur
        elif score >= 6:
            return 'confirmed'  # Bottom confirmé
        else:
            return 'simple'  # Bottom simple
    
    def backtest_strategy(self, bottoms_df, stop_loss_points=300, take_profit_mode='bb_mid'):
        """
        Backtest la stratégie sur les bottoms détectés
        
        Args:
            bottoms_df: DataFrame des bottoms détectés
            stop_loss_points: Points de stop loss sous le low
            take_profit_mode: 'bb_mid', 'bb_high', ou ratio R (ex: 5)
        """
        trades = []
        
        for idx, bottom in bottoms_df.iterrows():
            # Point d'entrée
            entry_idx = self.df.index.get_loc(bottom['timestamp'])
            entry_price = bottom['close']
            
            # Stop loss
            stop_loss = bottom['price'] - stop_loss_points
            risk = entry_price - stop_loss
            
            # Déterminer le take profit
            if take_profit_mode == 'bb_mid':
                take_profit = self.df['bb_mid'].iloc[entry_idx]
            elif take_profit_mode == 'bb_high':
                take_profit = self.df['bb_high'].iloc[entry_idx]
            elif isinstance(take_profit_mode, (int, float)):
                # Ratio R
                take_profit = entry_price + (risk * take_profit_mode)
            else:
                take_profit = entry_price * 1.10  # Default 10%
            
            # Simuler le trade
            trade_result = self.simulate_trade(
                entry_idx, 
                entry_price, 
                stop_loss, 
                take_profit
            )
            
            trade_result['score'] = bottom['score']
            trade_result['type'] = bottom['type']
            trades.append(trade_result)
        
        return self.calculate_backtest_metrics(pd.DataFrame(trades))
    
    def simulate_trade(self, entry_idx, entry_price, stop_loss, take_profit):
        """
        Simule un trade depuis le point d'entrée
        """
        max_bars = min(100, len(self.df) - entry_idx - 1)
        
        for i in range(1, max_bars):
            current_idx = entry_idx + i
            low = self.df['low'].iloc[current_idx]
            high = self.df['high'].iloc[current_idx]
            
            # Check stop loss
            if low <= stop_loss:
                return {
                    'entry': entry_price,
                    'exit': stop_loss,
                    'pnl': stop_loss - entry_price,
                    'pnl_pct': (stop_loss / entry_price - 1) * 100,
                    'bars_held': i,
                    'outcome': 'stop_loss'
                }
            
            # Check take profit
            if high >= take_profit:
                return {
                    'entry': entry_price,
                    'exit': take_profit,
                    'pnl': take_profit - entry_price,
                    'pnl_pct': (take_profit / entry_price - 1) * 100,
                    'bars_held': i,
                    'outcome': 'take_profit'
                }
        
        # Sortie au timeout
        exit_price = self.df['close'].iloc[entry_idx + max_bars - 1]
        return {
            'entry': entry_price,
            'exit': exit_price,
            'pnl': exit_price - entry_price,
            'pnl_pct': (exit_price / entry_price - 1) * 100,
            'bars_held': max_bars,
            'outcome': 'timeout'
        }
    
    def calculate_backtest_metrics(self, trades_df):
        """
        Calcule les métriques de backtest
        """
        if trades_df.empty:
            return {}
        
        wins = trades_df[trades_df['pnl'] > 0]
        losses = trades_df[trades_df['pnl'] < 0]
        
        metrics = {
            'total_trades': len(trades_df),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': len(wins) / len(trades_df) * 100,
            'avg_win': wins['pnl_pct'].mean() if not wins.empty else 0,
            'avg_loss': losses['pnl_pct'].mean() if not losses.empty else 0,
            'expectancy': trades_df['pnl_pct'].mean(),
            'profit_factor': abs(wins['pnl'].sum() / losses['pnl'].sum()) if not losses.empty and losses['pnl'].sum() != 0 else 0,
            'max_drawdown': self.calculate_max_drawdown(trades_df['pnl']),
            'sharpe_ratio': self.calculate_sharpe_ratio(trades_df['pnl_pct']),
            'avg_bars_held': trades_df['bars_held'].mean(),
            'by_score': trades_df.groupby('score')['pnl_pct'].agg(['count', 'mean', 'std']),
            'by_type': trades_df.groupby('type')['pnl_pct'].agg(['count', 'mean', 'std'])
        }
        
        return metrics
    
    def calculate_max_drawdown(self, pnl_series):
        """Calcule le drawdown maximum"""
        cumsum = pnl_series.cumsum()
        running_max = cumsum.expanding().max()
        drawdown = cumsum - running_max
        return drawdown.min()
    
    def calculate_sharpe_ratio(self, returns, periods_per_year=365*6):
        """Calcule le Sharpe Ratio"""
        if returns.std() == 0:
            return 0
        return np.sqrt(periods_per_year) * returns.mean() / returns.std()