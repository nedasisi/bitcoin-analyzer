"""
Module pour trouver l'heure exacte des bottoms en utilisant CryptoCompare API
API gratuite qui fonctionne partout et a des données historiques complètes
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import time

class ExactBottomFinder:
    def __init__(self):
        """Initialise avec CryptoCompare API (gratuite, pas de restrictions)"""
        # API CryptoCompare - pas besoin de clé pour les requêtes basiques
        self.api_base = "https://min-api.cryptocompare.com/data"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
    def get_minute_data_cryptocompare(self, start_time, end_time, symbol='BTC'):
        """Récupère les données 1 minute depuis CryptoCompare"""
        try:
            # CryptoCompare utilise des timestamps Unix
            end_ts = int(end_time.timestamp())
            
            # CryptoCompare limite à 2000 points par requête
            limit = min(2000, int((end_time - start_time).total_seconds() / 60))
            
            # Endpoint pour données minute historiques
            url = f"{self.api_base}/v2/histominute"
            
            params = {
                'fsym': symbol,
                'tsym': 'USD',
                'limit': limit,
                'toTs': end_ts,
                'e': 'CCCAGG'  # Aggregate de plusieurs exchanges
            }
            
            response = requests.get(url, params=params, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('Response') == 'Success' and data.get('Data', {}).get('Data'):
                    ohlcv_data = data['Data']['Data']
                    
                    # Convertir en DataFrame
                    df = pd.DataFrame(ohlcv_data)
                    
                    # Renommer les colonnes
                    df = df.rename(columns={
                        'time': 'timestamp',
                        'volumefrom': 'volume'
                    })
                    
                    # Convertir timestamp en datetime
                    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
                    df.set_index('datetime', inplace=True)
                    
                    # Filtrer pour la période exacte
                    df = df[(df.index >= start_time) & (df.index <= end_time)]
                    
                    print(f"✅ Données CryptoCompare: {len(df)} points")
                    return df
                    
            print(f"Erreur API CryptoCompare: {response.status_code}")
            return None
            
        except Exception as e:
            print(f"Erreur récupération données CryptoCompare: {e}")
            return None
    
    def get_minute_data_fallback_ccxt(self, start_time, end_time, symbol='BTC/USDT'):
        """Fallback sur CCXT si CryptoCompare échoue"""
        try:
            import ccxt
            
            # Essayer Bitget en fallback
            exchange = ccxt.bitget({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
            
            start_ts = int(start_time.timestamp() * 1000)
            
            ohlcv = exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe='1m',
                since=start_ts,
                limit=500
            )
            
            if ohlcv:
                df = pd.DataFrame(
                    ohlcv,
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                )
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('datetime', inplace=True)
                
                df = df[(df.index >= start_time) & (df.index <= end_time)]
                return df
                
        except:
            pass
            
        return None
    
    def get_minute_data(self, start_time, end_time, symbol='BTC/USDT'):
        """Récupère les données 1 minute avec fallback"""
        # Essayer CryptoCompare d'abord (meilleur historique)
        df = self.get_minute_data_cryptocompare(start_time, end_time, 'BTC')
        
        # Si échec, essayer CCXT
        if df is None or df.empty:
            df = self.get_minute_data_fallback_ccxt(start_time, end_time, symbol)
        
        return df
    
    def get_exact_bottom_time(self, bottom_time=None, approximate_time=None, **kwargs):
        """
        Trouve l'heure exacte du bottom à la minute près
        """
        # Extraire les paramètres
        symbol = kwargs.get('symbol', 'BTC/USDT')
        hours_before = kwargs.get('hours_before', 2)
        hours_after = kwargs.get('hours_after', 2)
        window_hours = kwargs.get('window_hours', None)
        
        # Support des deux noms d'arguments
        if approximate_time is not None:
            bottom_time = approximate_time
        
        if bottom_time is None:
            print("Erreur: Aucun temps de bottom fourni")
            return None
        
        # Si window_hours est spécifié
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
                    'source': 'no_data',
                    'note': 'Pas de données 1m disponibles'
                }
            
            # Trouver le minimum
            min_idx = df_1m['low'].idxmin()
            min_price = df_1m.loc[min_idx, 'low']
            
            # Calculer quelques statistiques
            price_at_bottom_candle = None
            bottom_4h = bottom_time.floor('4H')
            candle_data = df_1m[df_1m.index.floor('4H') == bottom_4h]
            if not candle_data.empty:
                price_at_bottom_candle = candle_data['low'].min()
            
            # Volume au moment du bottom
            volume_at_bottom = df_1m.loc[min_idx, 'volume'] if 'volume' in df_1m.columns else 0
            
            result = {
                'exact_time': min_idx,
                'exact_price': float(min_price),
                'original_time': bottom_time,
                'original_price': float(price_at_bottom_candle) if price_at_bottom_candle else kwargs.get('price', 0),
                'time_difference_minutes': (min_idx - bottom_time).total_seconds() / 60,
                'price_at_4h_candle': float(price_at_bottom_candle) if price_at_bottom_candle else kwargs.get('price', 0),
                'volume_at_bottom': float(volume_at_bottom),
                'data_points': len(df_1m),
                'source': 'cryptocompare',
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
                'source': 'error',
                'note': f'Erreur: {str(e)}'
            }
    
    def analyze_bottom_precision(self, bottoms_list, max_bottoms=10, **kwargs):
        """
        Analyse la précision temporelle d'une liste de bottoms
        """
        results = []
        sources_used = {}
        
        for i, bottom_time in enumerate(bottoms_list[:max_bottoms]):
            print(f"Analyse bottom {i+1}/{min(len(bottoms_list), max_bottoms)}: {bottom_time}")
            
            result = self.get_exact_bottom_time(bottom_time=bottom_time, **kwargs)
            if result:
                results.append(result)
                # Compter quelle source a été utilisée
                source = result.get('source', 'unknown')
                sources_used[source] = sources_used.get(source, 0) + 1
            
            # Pause pour respecter les limites API
            time.sleep(1.0)  # CryptoCompare a des limites sur l'API gratuite
        
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
                    'no_data': len(results) - len(valid_results),
                    'sources_used': sources_used
                }
            else:
                stats = {
                    'mean_time_diff': 0,
                    'median_time_diff': 0,
                    'std_time_diff': 0,
                    'max_time_diff': 0,
                    'total_analyzed': len(results),
                    'valid_results': 0,
                    'no_data': len(results),
                    'sources_used': sources_used
                }
            
            return df_results, stats
        
        return None, None