"""
Module pour trouver l'heure exacte des bottoms en utilisant Bitget
Version avec gestion des données manquantes
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
        # Date limite pour les données minute (Bitget n'a pas de données avant)
        self.min_date_for_minute_data = datetime(2021, 1, 1)
        
    def get_minute_data(self, start_time, end_time, symbol='BTC/USDT'):
        """Récupère les données 1 minute depuis Bitget"""
        try:
            # Vérifier si la date est trop ancienne
            if start_time < self.min_date_for_minute_data:
                print(f"Date trop ancienne pour données 1m: {start_time}")
                return None
                
            # Convertir en timestamps
            start_ts = int(start_time.timestamp() * 1000)
            end_ts = int(end_time.timestamp() * 1000)
            
            # Récupérer données 1m
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe='1m',
                since=start_ts,
                limit=500  # Max 500 bougies
            )
            
            if not ohlcv:
                return None
            
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
            print(f"Erreur récupération données 1m: {e}")
            return None
    
    def get_exact_bottom_time(self, bottom_time=None, approximate_time=None, **kwargs):
        """
        Trouve l'heure exacte du bottom à la minute près
        Version flexible qui accepte plusieurs formats d'arguments
        
        Args:
            bottom_time: datetime du bottom détecté sur 4H (legacy)
            approximate_time: datetime du bottom détecté (nouveau nom)
            **kwargs: Paramètres additionnels possibles
        """
        # Extraire les paramètres des kwargs
        symbol = kwargs.get('symbol', 'BTC/USDT')
        hours_before = kwargs.get('hours_before', 2)
        hours_after = kwargs.get('hours_after', 2)
        window_hours = kwargs.get('window_hours', None)
        
        # Support des deux noms d'arguments pour compatibilité
        if approximate_time is not None:
            bottom_time = approximate_time
        
        if bottom_time is None:
            print("Erreur: Aucun temps de bottom fourni")
            return None
        
        # Vérifier si la date est trop ancienne
        if pd.Timestamp(bottom_time).tz_localize(None) < self.min_date_for_minute_data:
            # Pour les dates anciennes, retourner une estimation basée sur la bougie 4H
            return {
                'exact_time': bottom_time,
                'exact_price': kwargs.get('price', 0),
                'original_time': bottom_time,
                'original_price': kwargs.get('price', 0),
                'time_difference_minutes': 0,
                'price_at_4h_candle': kwargs.get('price', 0),
                'volume_at_bottom': 0,
                'data_points': 0,
                'note': 'Données 1m non disponibles pour cette date (trop ancienne)'
            }
        
        # Si window_hours est spécifié, l'utiliser pour définir before/after
        if window_hours is not None:
            hours_before = window_hours / 2
            hours_after = window_hours / 2
        
        try:
            # Définir la période à analyser
            start_time = bottom_time - timedelta(hours=hours_before)
            end_time = bottom_time + timedelta(hours=hours_after)
            
            # Récupérer les données 1 minute
            df_1m = self.get_minute_data(start_time, end_time, symbol)
            
            if df_1m is None or df_1m.empty:
                # Retourner les données de la bougie 4H comme fallback
                return {
                    'exact_time': bottom_time,
                    'exact_price': kwargs.get('price', 0),
                    'original_time': bottom_time,
                    'original_price': kwargs.get('price', 0),
                    'time_difference_minutes': 0,
                    'price_at_4h_candle': kwargs.get('price', 0),
                    'volume_at_bottom': 0,
                    'data_points': 0,
                    'note': 'Données 1m non disponibles'
                }
            
            # Trouver le minimum
            min_idx = df_1m['low'].idxmin()
            min_price = df_1m.loc[min_idx, 'low']
            
            # Calculer quelques statistiques
            price_at_bottom_candle = df_1m[df_1m.index.floor('4H') == bottom_time.floor('4H')]['low'].min() if not df_1m[df_1m.index.floor('4H') == bottom_time.floor('4H')].empty else None
            
            # Volume au moment du bottom
            volume_at_bottom = df_1m.loc[min_idx, 'volume'] if 'volume' in df_1m.columns else None
            
            result = {
                'exact_time': min_idx,
                'exact_price': min_price,
                'original_time': bottom_time,
                'original_price': price_at_bottom_candle,
                'time_difference_minutes': (min_idx - bottom_time).total_seconds() / 60,
                'price_at_4h_candle': price_at_bottom_candle,
                'volume_at_bottom': volume_at_bottom,
                'data_points': len(df_1m),
                'note': 'OK'
            }
            
            return result
            
        except Exception as e:
            print(f"Erreur dans get_exact_bottom_time: {e}")
            # Retourner les données de base en cas d'erreur
            return {
                'exact_time': bottom_time,
                'exact_price': kwargs.get('price', 0),
                'original_time': bottom_time,
                'original_price': kwargs.get('price', 0),
                'time_difference_minutes': 0,
                'price_at_4h_candle': kwargs.get('price', 0),
                'volume_at_bottom': 0,
                'data_points': 0,
                'note': f'Erreur: {str(e)}'
            }
    
    def analyze_bottom_precision(self, bottoms_list, max_bottoms=10, **kwargs):
        """
        Analyse la précision temporelle d'une liste de bottoms
        
        Args:
            bottoms_list: Liste des bottoms à analyser
            max_bottoms: Nombre maximum de bottoms à analyser
            **kwargs: Paramètres additionnels passés à get_exact_bottom_time
        """
        results = []
        
        for i, bottom_time in enumerate(bottoms_list[:max_bottoms]):
            print(f"Analyse bottom {i+1}/{min(len(bottoms_list), max_bottoms)}: {bottom_time}")
            
            result = self.get_exact_bottom_time(bottom_time=bottom_time, **kwargs)
            if result:
                results.append(result)
            
            # Pause pour respecter les limites
            time.sleep(0.5)
        
        # Créer un DataFrame avec les résultats
        if results:
            df_results = pd.DataFrame(results)
            
            # Filtrer les résultats valides pour les statistiques
            valid_results = df_results[df_results['data_points'] > 0]
            
            if not valid_results.empty:
                stats = {
                    'mean_time_diff': valid_results['time_difference_minutes'].mean(),
                    'median_time_diff': valid_results['time_difference_minutes'].median(),
                    'std_time_diff': valid_results['time_difference_minutes'].std(),
                    'max_time_diff': valid_results['time_difference_minutes'].abs().max(),
                    'total_analyzed': len(results),
                    'valid_results': len(valid_results),
                    'old_data_skipped': len(results) - len(valid_results)
                }
            else:
                stats = {
                    'mean_time_diff': 0,
                    'median_time_diff': 0,
                    'std_time_diff': 0,
                    'max_time_diff': 0,
                    'total_analyzed': len(results),
                    'valid_results': 0,
                    'old_data_skipped': len(results)
                }
            
            return df_results, stats
        
        return None, None