"""
Module pour récupérer l'heure exacte des bottoms avec données 1 minute
"""

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

class ExactBottomFinder:
    def __init__(self, exchange_name='binance'):
        """
        Initialise le module de recherche exacte des bottoms
        """
        self.exchange = getattr(ccxt, exchange_name)({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future' if exchange_name == 'binance' else 'swap'
            }
        })
    
    def get_exact_bottom_time(self, approximate_time, symbol='BTC/USDT:USDT', window_hours=4):
        """
        Récupère l'heure exacte d'un bottom en analysant les données 1m
        
        Args:
            approximate_time: Timestamp approximatif du bottom (depuis bougie 4h)
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
            
            # Trouver le minimum exact
            min_idx = df_1m['low'].idxmin()
            min_price = df_1m['low'].min()
            
            # Analyser la bougie du minimum pour être encore plus précis
            min_candle = df_1m.loc[min_idx]
            
            # Estimer la seconde dans la minute
            if min_candle['close'] < min_candle['open']:
                # Bougie baissière - minimum probablement vers la fin
                estimated_second = 45
            elif abs(min_candle['low'] - min_candle['open']) < abs(min_candle['low'] - min_candle['close']):
                # Minimum proche de l'open
                estimated_second = 15
            else:
                # Minimum au milieu
                estimated_second = 30
            
            exact_time = min_idx + timedelta(seconds=estimated_second)
            
            return {
                'exact_time': exact_time,
                'exact_price': min_price,
                'candle_time': min_idx,
                'precision': '±30 secondes',
                'volume_at_bottom': min_candle['volume']
            }
            
        except Exception as e:
            print(f"Erreur lors de la récupération des données 1m: {e}")
            return None
    
    def get_multiple_exact_bottoms(self, bottoms_df, symbol='BTC/USDT:USDT'):
        """
        Récupère l'heure exacte pour plusieurs bottoms
        """
        exact_times = []
        
        for idx, row in bottoms_df.iterrows():
            print(f"Recherche heure exacte pour {idx}...")
            exact_data = self.get_exact_bottom_time(idx, symbol)
            
            if exact_data:
                exact_times.append({
                    'original_time': idx,
                    **exact_data
                })
            
            # Pause pour respecter les limites API
            time.sleep(1)
        
        return pd.DataFrame(exact_times)