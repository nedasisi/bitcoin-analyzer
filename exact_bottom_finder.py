"""
Module pour trouver l'heure exacte des bottoms en utilisant Bitget
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import time

class ExactBottomFinder:
    def __init__(self):
        """Initialise la connexion à Bitget uniquement"""
        self.exchange = ccxt.bitget({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot'
            }
        })
        
    def get_minute_data(self, start_time, end_time):
        """Récupère les données 1 minute depuis Bitget"""
        try:
            # Convertir en timestamps
            start_ts = int(start_time.timestamp() * 1000)
            end_ts = int(end_time.timestamp() * 1000)
            
            # Récupérer données 1m
            ohlcv = self.exchange.fetch_ohlcv(
                symbol='BTC/USDT',
                timeframe='1m',
                since=start_ts,
                limit=500  # Max 500 bougies
            )
            
            # Convertir en DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('datetime', inplace=True)
            
            # Filtrer pour la période exacte
            df = df[(df.index >= start_time) & (df.index <= end_time)]
            
            return df
            
        except Exception as e:
            print(f"Erreur récupération données 1m depuis Bitget: {e}")
            return None
    
    def get_exact_bottom_time(self, bottom_time=None, approximate_time=None, hours_before=2, hours_after=2):
        """
        Trouve l'heure exacte du bottom à la minute près
        
        Args:
            bottom_time: datetime du bottom détecté sur 4H (legacy)
            approximate_time: datetime du bottom détecté (nouveau nom)
            hours_before: heures à analyser avant le bottom
            hours_after: heures à analyser après le bottom
        """
        # Support des deux noms d'arguments pour compatibilité
        if approximate_time is not None:
            bottom_time = approximate_time
        
        if bottom_time is None:
            print("Erreur: Aucun temps de bottom fourni")
            return None
        try:
            # Définir la période à analyser
            start_time = bottom_time - timedelta(hours=hours_before)
            end_time = bottom_time + timedelta(hours=hours_after)
            
            # Récupérer les données 1 minute
            df_1m = self.get_minute_data(start_time, end_time)
            
            if df_1m is None or df_1m.empty:
                print(f"Pas de données 1m pour {bottom_time}")
                return None
            
            # Trouver le minimum
            min_idx = df_1m['low'].idxmin()
            min_price = df_1m.loc[min_idx, 'low']
            
            # Calculer quelques statistiques
            price_at_bottom_candle = df_1m[df_1m.index.floor('4H') == bottom_time.floor('4H')]['low'].min() if not df_1m[df_1m.index.floor('4H') == bottom_time.floor('4H')].empty else None
            
            result = {
                'exact_time': min_idx,
                'exact_price': min_price,
                'original_time': bottom_time,
                'time_difference_minutes': (min_idx - bottom_time).total_seconds() / 60,
                'price_at_4h_candle': price_at_bottom_candle,
                'data_points': len(df_1m)
            }
            
            return result
            
        except Exception as e:
            print(f"Erreur dans get_exact_bottom_time: {e}")
            return None
    
    def analyze_bottom_precision(self, bottoms_list, max_bottoms=10):
        """
        Analyse la précision temporelle d'une liste de bottoms
        """
        results = []
        
        for i, bottom_time in enumerate(bottoms_list[:max_bottoms]):
            print(f"Analyse bottom {i+1}/{min(len(bottoms_list), max_bottoms)}: {bottom_time}")
            
            result = self.get_exact_bottom_time(bottom_time)
            if result:
                results.append(result)
            
            # Pause pour respecter les limites
            time.sleep(0.5)
        
        # Créer un DataFrame avec les résultats
        if results:
            df_results = pd.DataFrame(results)
            
            # Statistiques
            stats = {
                'mean_time_diff': df_results['time_difference_minutes'].mean(),
                'median_time_diff': df_results['time_difference_minutes'].median(),
                'std_time_diff': df_results['time_difference_minutes'].std(),
                'max_time_diff': df_results['time_difference_minutes'].abs().max(),
                'total_analyzed': len(results)
            }
            
            return df_results, stats
        
        return None, None