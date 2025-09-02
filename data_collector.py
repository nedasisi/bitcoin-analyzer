"""
Module de collecte de données depuis Bitget ou alternatives
"""

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
from config import *

class DataCollector:
    def __init__(self, timeframe=None):
        """Initialise le collecteur de données"""
        self.exchange = None
        self.timeframe = timeframe or TIMEFRAME
        self.init_exchange()
        
    def init_exchange(self):
        """Initialise la connexion à l'exchange"""
        try:
            # Utiliser Bitget via CCXT
            self.exchange = ccxt.bitget({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'swap',  # Pour les futures perpetual
                }
            })
        except Exception as e:
            print(f"Erreur connexion Bitget: {e}")
            # Fallback sur Binance si Bitget fail
            self.exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',
                }
            })
    
    def fetch_ohlcv_data(self, symbol=SYMBOL, timeframe=None, since=None, limit=500):
        """
        Récupère les données OHLCV
        """
        if timeframe is None:
            timeframe = self.timeframe
        try:
            if since is None:
                since = int(datetime.strptime(START_DATE, "%Y-%m-%d").timestamp() * 1000)
            
            all_data = []
            
            while True:
                try:
                    # Récupérer les données par batch
                    ohlcv = self.exchange.fetch_ohlcv(
                        symbol=symbol,
                        timeframe=timeframe,
                        since=since,
                        limit=limit
                    )
                    
                    if not ohlcv:
                        break
                    
                    all_data.extend(ohlcv)
                    
                    # Mise à jour du timestamp pour la prochaine requête
                    since = ohlcv[-1][0] + 1
                    
                    # Si on arrive à aujourd'hui, on arrête
                    if since > int(datetime.now().timestamp() * 1000):
                        break
                    
                    # Pause pour respecter rate limit
                    time.sleep(self.exchange.rateLimit / 1000)
                    
                except Exception as e:
                    print(f"Erreur fetch batch: {e}")
                    break
            
            # Convertir en DataFrame
            df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            print(f"Erreur fetch_ohlcv_data: {e}")
            return None
    
    def get_historical_data(self, use_cache=USE_CACHE):
        """
        Récupère les données historiques avec gestion du cache
        """
        # Nom du fichier de cache incluant le timeframe
        cache_path = f"data/btc_history_{self.timeframe}.csv"
        
        # Créer le dossier data si nécessaire
        os.makedirs(os.path.dirname(cache_path) if os.path.dirname(cache_path) else ".", exist_ok=True)
        
        # Vérifier le cache
        if use_cache and os.path.exists(cache_path):
            try:
                # Lire le cache
                df = pd.read_csv(cache_path, index_col='timestamp', parse_dates=True)
                
                # Vérifier l'âge du cache
                last_update = df.index[-1]
                hours_old = (datetime.now() - last_update.to_pydatetime()).total_seconds() / 3600
                
                if hours_old < CACHE_EXPIRY_HOURS:
                    print(f"✅ Données chargées depuis le cache ({hours_old:.1f}h)")
                    return df
                else:
                    print(f"📊 Cache expiré, mise à jour...")
                    # Récupérer seulement les nouvelles données
                    new_data = self.fetch_ohlcv_data(
                        since=int(last_update.timestamp() * 1000)
                    )
                    if new_data is not None and not new_data.empty:
                        df = pd.concat([df, new_data]).drop_duplicates()
                        df.sort_index(inplace=True)
                        df.to_csv(cache_path)
                    return df
                    
            except Exception as e:
                print(f"Erreur lecture cache: {e}")
        
        # Pas de cache ou erreur : récupérer toutes les données
        print("📥 Téléchargement des données historiques...")
        df = self.fetch_ohlcv_data()
        
        if df is not None and not df.empty:
            # Sauvegarder en cache
            df.to_csv(cache_path)
            print(f"✅ {len(df)} bougies sauvegardées")
        
        return df
    
    def add_technical_indicators(self, df):
        """
        Ajoute les indicateurs techniques
        """
        import ta
        
        # RSI
        df['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()
        
        # Moyennes mobiles
        df['sma_20'] = ta.trend.SMAIndicator(close=df['close'], window=20).sma_indicator()
        df['sma_50'] = ta.trend.SMAIndicator(close=df['close'], window=50).sma_indicator()
        
        # Bollinger Bands
        bb = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
        df['bb_lower'] = bb.bollinger_lband()
        df['bb_upper'] = bb.bollinger_hband()
        
        # Volume moyen
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Range
        df['range'] = df['high'] - df['low']
        df['range_pct'] = (df['range'] / df['close']) * 100
        
        return df
    
    def estimate_liquidations(self, df):
        """
        Estime les liquidations basées sur volume et volatilité
        """
        # Spike de volume + grande bougie = liquidations probables
        df['volume_spike'] = df['volume_ratio'] > 3
        df['price_spike'] = df['range_pct'] > df['range_pct'].rolling(50).mean() * 2
        df['liquidation_signal'] = df['volume_spike'] & df['price_spike']
        
        return df

# Fonction utilitaire pour tester
if __name__ == "__main__":
    collector = DataCollector()
    df = collector.get_historical_data()
    if df is not None:
        print(f"\n📊 Données récupérées:")
        print(f"Période: {df.index[0]} à {df.index[-1]}")
        print(f"Nombre de bougies: {len(df)}")
        print(f"\nDernières données:")
        print(df.tail())