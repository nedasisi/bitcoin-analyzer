"""
Version allégée du data collector pour production
Utilise des données en cache pour éviter les limites API
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st
import ccxt
import time

class DataCollector:
    def __init__(self, exchange='binance', use_cache=True):
        self.use_cache = use_cache
        self.exchange_name = exchange
        
        # En production, limiter les appels API
        if self.should_use_live_api():
            self.exchange = getattr(ccxt, exchange)({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future' if exchange == 'binance' else 'swap'
                }
            })
        else:
            self.exchange = None
    
    def should_use_live_api(self):
        """Détermine si on peut utiliser l'API live"""
        # En production, utiliser le cache sauf si explicitement demandé
        import os
        is_deployed = os.environ.get('STREAMLIT_RUNTIME_ENV') == 'cloud'
        
        if is_deployed:
            # En production : toujours utiliser le cache
            return False
        else:
            # En local : utiliser l'API
            return True
    
    @st.cache_data(ttl=3600)  # Cache 1 heure
    def get_historical_data(self, symbol='BTC/USDT:USDT', timeframe='4h', limit=1000):
        """
        Récupère les données historiques avec cache agressif
        """
        
        # En production, utiliser des données de démonstration
        if not self.should_use_live_api():
            return self.get_demo_data(timeframe, limit)
        
        # En local, utiliser l'API réelle
        try:
            since = int((datetime.now() - timedelta(days=365*2)).timestamp() * 1000)
            
            all_candles = []
            while len(all_candles) < limit:
                candles = self.exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    since=since,
                    limit=min(500, limit - len(all_candles))
                )
                
                if not candles:
                    break
                
                all_candles.extend(candles)
                since = candles[-1][0] + 1
                
                # Pause pour respecter rate limits
                time.sleep(self.exchange.rateLimit / 1000)
                
                # Limite de sécurité
                if len(all_candles) >= limit:
                    break
            
            # Convertir en DataFrame
            df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            st.warning(f"Impossible de charger les données live: {e}")
            return self.get_demo_data(timeframe, limit)
    
    def get_demo_data(self, timeframe='4h', limit=1000):
        """
        Génère des données de démonstration réalistes
        """
        # Créer des données synthétiques basées sur des patterns réels
        np.random.seed(42)  # Pour reproductibilité
        
        # Déterminer l'intervalle selon le timeframe
        if timeframe == '1h':
            freq = 'H'
            periods = limit
        elif timeframe == '4h':
            freq = '4H'
            periods = limit
        else:  # 1d
            freq = 'D'
            periods = limit
        
        # Générer les dates
        dates = pd.date_range(end=datetime.now(), periods=periods, freq=freq)
        
        # Générer des prix réalistes (simulation de Bitcoin)
        base_price = 50000
        prices = []
        current_price = base_price
        
        for i in range(periods):
            # Ajouter de la volatilité réaliste
            change = np.random.normal(0, 0.02)  # 2% de volatilité
            
            # Ajouter des trends
            if i % 100 < 50:
                change += 0.001  # Trend haussier
            else:
                change -= 0.001  # Trend baissier
            
            # Ajouter des crashes/pumps occasionnels
            if np.random.random() < 0.05:  # 5% de chance
                change *= 3  # Triple volatilité
            
            current_price *= (1 + change)
            current_price = max(10000, min(150000, current_price))  # Limites réalistes
            prices.append(current_price)
        
        # Créer le DataFrame OHLCV
        df = pd.DataFrame(index=dates)
        df['close'] = prices
        
        # Générer OHLV à partir du close
        df['open'] = df['close'].shift(1).fillna(df['close'].iloc[0])
        df['high'] = df[['open', 'close']].max(axis=1) * np.random.uniform(1.001, 1.02, periods)
        df['low'] = df[['open', 'close']].min(axis=1) * np.random.uniform(0.98, 0.999, periods)
        
        # Volume réaliste
        df['volume'] = np.random.lognormal(20, 1, periods) * 1000000
        
        # Ajouter quelques bottoms et tops évidents
        for i in range(5, len(df)-5, 50):
            if i % 100 < 50:  # Bottom
                df.iloc[i]['low'] *= 0.95
                df.iloc[i]['close'] = df.iloc[i]['low'] * 1.01
            else:  # Top
                df.iloc[i]['high'] *= 1.05
                df.iloc[i]['close'] = df.iloc[i]['high'] * 0.99
        
        return df
    
    def add_technical_indicators(self, df):
        """Ajoute les indicateurs techniques essentiels"""
        from ta.momentum import RSIIndicator
        from ta.volatility import BollingerBands
        
        # RSI
        rsi = RSIIndicator(close=df['close'], window=14)
        df['rsi'] = rsi.rsi()
        
        # Bollinger Bands
        bb = BollingerBands(close=df['close'], window=20, window_dev=2)
        df['bb_high'] = bb.bollinger_hband()
        df['bb_mid'] = bb.bollinger_mavg()
        df['bb_low'] = bb.bollinger_lband()
        df['bb_width'] = df['bb_high'] - df['bb_low']
        
        # Volume moyen
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        return df
    
    def estimate_liquidations(self, df):
        """Estime les zones de liquidation (simplifié pour production)"""
        # Version simplifiée pour éviter les calculs lourds
        df['liq_long'] = df['low'] * 0.95  # Estimation 5% sous les lows
        df['liq_short'] = df['high'] * 1.05  # Estimation 5% au-dessus des highs
        
        return df