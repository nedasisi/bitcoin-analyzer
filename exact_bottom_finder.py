"""
Module pour trouver l'heure exacte des bottoms en utilisant plusieurs exchanges
Version multi-exchange pour maximiser la couverture de données
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import time

class ExactBottomFinder:
    def __init__(self):
        """Initialise plusieurs exchanges pour maximiser la disponibilité des données"""
        self.exchanges = {}
        self.init_exchanges()
        
    def init_exchanges(self):
        """Initialise plusieurs exchanges en fallback"""
        # Bitget (principal pour Streamlit Cloud)
        try:
            self.exchanges['bitget'] = ccxt.bitget({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
        except:
            pass
            
        # KuCoin (bon historique)
        try:
            self.exchanges['kucoin'] = ccxt.kucoin({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
        except:
            pass
            
        # Bybit (données historiques)
        try:
            self.exchanges['bybit'] = ccxt.bybit({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
        except:
            pass
            
        # Gate.io (bon historique aussi)
        try:
            self.exchanges['gateio'] = ccxt.gateio({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
        except:
            pass
        
        # Date limite estimée pour chaque exchange
        self.min_dates = {
            'bitget': datetime(2021, 1, 1),
            'kucoin': datetime(2019, 1, 1),
            'bybit': datetime(2020, 1, 1),
            'gateio': datetime(2018, 1, 1)
        }
        
    def get_minute_data(self, start_time, end_time, symbol='BTC/USDT'):
        """Récupère les données 1 minute depuis le premier exchange disponible"""
        
        # Essayer chaque exchange
        for name, exchange in self.exchanges.items():
            if not exchange:
                continue
                
            # Vérifier si l'exchange a probablement des données pour cette période
            min_date = self.min_dates.get(name, datetime(2021, 1, 1))
            if start_time < min_date:
                continue
                
            try:
                print(f"Essai avec {name}...")
                
                # Convertir en timestamps
                start_ts = int(start_time.timestamp() * 1000)
                
                # Récupérer données 1m
                ohlcv = exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe='1m',
                    since=start_ts,
                    limit=500  # Max 500 bougies
                )
                
                if ohlcv and len(ohlcv) > 0:
                    # Convertir en DataFrame
                    df = pd.DataFrame(
                        ohlcv,
                        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                    )
                    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('datetime', inplace=True)
                    
                    # Filtrer pour la période exacte
                    df = df[(df.index >= start_time) & (df.index <= end_time)]
                    
                    if not df.empty:
                        print(f"✅ Données trouvées sur {name}: {len(df)} points")
                        return df, name
                        
            except Exception as e:
                print(f"Erreur avec {name}: {e}")
                continue
        
        return None, None
    
    def get_exact_bottom_time(self, bottom_time=None, approximate_time=None, **kwargs):
        """
        Trouve l'heure exacte du bottom à la minute près
        Version multi-exchange
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
            
            # Récupérer les données 1 minute depuis n'importe quel exchange
            df_1m, exchange_used = self.get_minute_data(start_time, end_time, symbol)
            
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
                    'exchange_used': 'none',
                    'note': 'Pas de données 1m disponibles'
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
                'exchange_used': exchange_used,
                'note': f'OK - Données de {exchange_used}'
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
                'exchange_used': 'error',
                'note': f'Erreur: {str(e)}'
            }
    
    def analyze_bottom_precision(self, bottoms_list, max_bottoms=10, **kwargs):
        """
        Analyse la précision temporelle d'une liste de bottoms
        """
        results = []
        exchanges_used = {}
        
        for i, bottom_time in enumerate(bottoms_list[:max_bottoms]):
            print(f"Analyse bottom {i+1}/{min(len(bottoms_list), max_bottoms)}: {bottom_time}")
            
            result = self.get_exact_bottom_time(bottom_time=bottom_time, **kwargs)
            if result:
                results.append(result)
                # Compter quel exchange a été utilisé
                exchange = result.get('exchange_used', 'none')
                exchanges_used[exchange] = exchanges_used.get(exchange, 0) + 1
            
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
                    'old_data_skipped': len(results) - len(valid_results),
                    'exchanges_used': exchanges_used
                }
            else:
                stats = {
                    'mean_time_diff': 0,
                    'median_time_diff': 0,
                    'std_time_diff': 0,
                    'max_time_diff': 0,
                    'total_analyzed': len(results),
                    'valid_results': 0,
                    'old_data_skipped': len(results),
                    'exchanges_used': exchanges_used
                }
            
            return df_results, stats
        
        return None, None