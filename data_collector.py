"""
Module de collecte de données depuis CryptoCompare pour l'historique complet
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
import requests
from config import *

class DataCollector:
    def __init__(self, timeframe=None):
        """Initialise le collecteur de données"""
        self.timeframe = timeframe or TIMEFRAME
        self.api_base = "https://min-api.cryptocompare.com/data"
        
    def fetch_ohlcv_data(self, symbol='BTC', timeframe=None, since=None, limit=2000):
        """
        Récupère les données OHLCV depuis CryptoCompare
        """
        if timeframe is None:
            timeframe = self.timeframe
            
        try:
            # Mapper les timeframes vers les endpoints CryptoCompare
            endpoint_map = {
                '1m': 'histominute',
                '5m': 'histominute',
                '15m': 'histominute', 
                '30m': 'histominute',
                '1h': 'histohour',
                '2h': 'histohour',
                '4h': 'histohour',
                '1d': 'histoday'
            }
            
            # Calculer l'agrégation nécessaire
            aggregate_map = {
                '1m': 1,
                '5m': 5,
                '15m': 15,
                '30m': 30,
                '1h': 1,
                '2h': 2,
                '4h': 4,
                '1d': 1
            }
            
            endpoint = endpoint_map.get(timeframe, 'histohour')
            aggregate = aggregate_map.get(timeframe, 1)
            
            # Calculer le timestamp de fin (maintenant)
            to_ts = int(datetime.now().timestamp())
            
            # URL de l'API
            url = f"{self.api_base}/v2/{endpoint}"
            
            all_data = []
            
            # CryptoCompare limite à 2000 points par requête
            # Pour obtenir tout l'historique, on fait plusieurs requêtes
            while True:
                params = {
                    'fsym': symbol,
                    'tsym': 'USD',
                    'limit': 2000,
                    'toTs': to_ts,
                    'aggregate': aggregate
                }
                
                response = requests.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get('Response') == 'Success' and data.get('Data', {}).get('Data'):
                        ohlcv_data = data['Data']['Data']
                        
                        # Ajouter les données
                        all_data = ohlcv_data + all_data
                        
                        # Si on a atteint la date de début souhaitée
                        if since:
                            first_timestamp = ohlcv_data[0]['time'] * 1000
                            if first_timestamp <= since:
                                break
                        
                        # Préparer pour la prochaine requête
                        to_ts = ohlcv_data[0]['time'] - 1
                        
                        # Si on remonte avant 2010, arrêter
                        if to_ts < int(datetime(2010, 1, 1).timestamp()):
                            break
                        
                        # Limite de sécurité
                        if len(all_data) > 100000:  # ~11 ans de données 4H
                            break
                        
                        # Pause pour éviter le rate limiting
                        time.sleep(0.2)
                    else:
                        break
                else:
                    print(f"Erreur API CryptoCompare: {response.status_code}")
                    break
            
            # Convertir en DataFrame
            if all_data:
                df = pd.DataFrame(all_data)
                
                # Renommer les colonnes
                df = df.rename(columns={
                    'time': 'timestamp',
                    'volumefrom': 'volume'
                })
                
                # Convertir timestamp en datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                df.set_index('timestamp', inplace=True)
                
                # Filtrer depuis la date de début
                if since:
                    start_date = pd.to_datetime(since, unit='ms')
                    df = df[df.index >= start_date]
                
                print(f"✅ {len(df)} bougies récupérées depuis CryptoCompare")
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
                    since_ts = int(last_update.timestamp() * 1000)
                    new_data = self.fetch_ohlcv_data(since=since_ts)
                    
                    if new_data is not None and not new_data.empty:
                        df = pd.concat([df, new_data]).drop_duplicates()
                        df.sort_index(inplace=True)
                        df.to_csv(cache_path)
                    return df
                    
            except Exception as e:
                print(f"Erreur lecture cache: {e}")
        
        # Pas de cache ou erreur : récupérer toutes les données
        print("📥 Téléchargement des données historiques depuis CryptoCompare...")
        
        # Convertir la date de début en timestamp
        since_ts = int(datetime.strptime(START_DATE, "%Y-%m-%d").timestamp() * 1000)
        
        df = self.fetch_ohlcv_data(since=since_ts)
        
        if df is not None and not df.empty:
            # Sauvegarder en cache
            df.to_csv(cache_path)
            print(f"✅ {len(df)} bougies sauvegardées")
        
        return df
    
    def add_technical_indicators(self, df):
        """
        Ajoute les indicateurs techniques
        """
        if df is None or df.empty:
            return df
            
        try:
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
            
        except Exception as e:
            print(f"Erreur ajout indicateurs: {e}")
        
        return df
    
    def estimate_liquidations(self, df):
        """
        Estime les liquidations basées sur volume et volatilité
        """
        if df is None or df.empty:
            return df
            
        try:
            # Spike de volume + grande bougie = liquidations probables
            df['volume_spike'] = df['volume_ratio'] > 3
            df['price_spike'] = df['range_pct'] > df['range_pct'].rolling(50).mean() * 2
            df['liquidation_signal'] = df['volume_spike'] & df['price_spike']
        except:
            pass
        
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