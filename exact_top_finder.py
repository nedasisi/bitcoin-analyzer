"""
Module pour trouver l'heure exacte des tops avec données 1 minute
Miroir du exact_bottom_finder mais pour les sommets
"""

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

class ExactTopFinder:
    def __init__(self, exchange_name='binance'):
        """
        Initialise le module de recherche exacte des tops
        """
        self.exchange = getattr(ccxt, exchange_name)({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future' if exchange_name == 'binance' else 'swap'
            }
        })
    
    def get_exact_top_time(self, approximate_time, symbol='BTC/USDT:USDT', window_hours=4):
        """
        Récupère l'heure exacte d'un top en analysant les données 1m
        
        Args:
            approximate_time: Timestamp approximatif du top (depuis bougie 4h)
            symbol: Symbole à analyser
            window_hours: Fenêtre de recherche en heures (ex: 4 pour une bougie 4h)
        
        Returns:
            dict avec l'heure exacte et le prix exact
        """
        try:
            # Définir la fenêtre de recherche
            start_time = approximate_time - timedelta(hours=window_hours/2)
            end_time = approximate_time + timedelta(hours=window_hours/2)
            
            # Convertir en millisecondes pour l'API
            since = int(start_time.timestamp() * 1000)
            
            # Récupérer les données 1 minute
            ohlcv_1m = []
            current_time = since
            
            while current_time < int(end_time.timestamp() * 1000):
                batch = self.exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe='1m',
                    since=current_time,
                    limit=1000  # Max par requête
                )
                
                if not batch:
                    break
                
                ohlcv_1m.extend(batch)
                current_time = batch[-1][0] + 60000  # +1 minute
                time.sleep(self.exchange.rateLimit / 1000)
            
            # Convertir en DataFrame
            df_1m = pd.DataFrame(ohlcv_1m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df_1m['timestamp'] = pd.to_datetime(df_1m['timestamp'], unit='ms')
            df_1m.set_index('timestamp', inplace=True)
            
            # Trouver le maximum exact
            max_idx = df_1m['high'].idxmax()
            max_price = df_1m['high'].max()
            
            # Analyser la bougie du maximum pour être encore plus précis
            max_candle = df_1m.loc[max_idx]
            
            # Estimer la seconde dans la minute
            if max_candle['close'] > max_candle['open']:
                # Bougie haussière - maximum probablement vers la fin
                estimated_second = 45
            elif abs(max_candle['high'] - max_candle['open']) < abs(max_candle['high'] - max_candle['close']):
                # Maximum proche de l'open
                estimated_second = 15
            else:
                # Maximum au milieu
                estimated_second = 30
            
            exact_time = max_idx + timedelta(seconds=estimated_second)
            
            return {
                'exact_time': exact_time,
                'exact_price': max_price,
                'candle_time': max_idx,
                'precision': '±30 secondes',
                'volume_at_top': max_candle['volume']
            }
            
        except Exception as e:
            print(f"Erreur lors de la récupération des données 1m pour top: {e}")
            return None
    
    def get_multiple_exact_tops(self, tops_df, symbol='BTC/USDT:USDT'):
        """
        Récupère l'heure exacte pour plusieurs tops
        """
        exact_times = []
        
        for idx, row in tops_df.iterrows():
            print(f"Recherche heure exacte pour top {idx}...")
            exact_data = self.get_exact_top_time(idx, symbol)
            
            if exact_data:
                exact_times.append({
                    'original_time': idx,
                    **exact_data
                })
            
            # Pause pour respecter les limites API
            time.sleep(1)
        
        return pd.DataFrame(exact_times)