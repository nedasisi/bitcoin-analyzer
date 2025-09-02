"""
Module avancé pour récupérer les données tick-by-tick et WebSocket
"""

import asyncio
import websockets
import json
import pandas as pd
from datetime import datetime, timedelta
import requests

class TickDataCollector:
    """
    Collecteur de données tick-by-tick pour précision maximale
    """
    
    def __init__(self):
        self.trades_data = []
        
    def get_historical_trades_binance(self, symbol='BTCUSDT', start_time=None, end_time=None):
        """
        Récupère les trades historiques de Binance
        API: https://api.binance.com/api/v3/aggTrades
        
        Précision: Trade exact à la milliseconde
        """
        base_url = "https://api.binance.com/api/v3/aggTrades"
        
        all_trades = []
        current_time = start_time
        
        while current_time < end_time:
            params = {
                'symbol': symbol,
                'startTime': int(current_time.timestamp() * 1000),
                'endTime': int(end_time.timestamp() * 1000),
                'limit': 1000  # Max 1000 par requête
            }
            
            response = requests.get(base_url, params=params)
            
            if response.status_code == 200:
                trades = response.json()
                if not trades:
                    break
                    
                all_trades.extend(trades)
                
                # Mettre à jour le temps pour la prochaine requête
                last_trade_time = trades[-1]['T']  # Timestamp du dernier trade
                current_time = datetime.fromtimestamp(last_trade_time / 1000) + timedelta(milliseconds=1)
                
                # Pause pour éviter rate limit
                time.sleep(0.1)
            else:
                print(f"Erreur API: {response.status_code}")
                break
        
        # Convertir en DataFrame
        if all_trades:
            df = pd.DataFrame(all_trades)
            df['time'] = pd.to_datetime(df['T'], unit='ms')
            df['price'] = df['p'].astype(float)
            df['quantity'] = df['q'].astype(float)
            
            # Trouver le minimum exact
            min_idx = df['price'].idxmin()
            min_trade = df.loc[min_idx]
            
            return {
                'exact_time': min_trade['time'],
                'exact_price': min_trade['price'],
                'exact_quantity': min_trade['quantity'],
                'trade_id': min_trade['a'],  # Aggregate trade ID
                'precision': 'Exact (milliseconde)',
                'is_buyer_maker': min_trade['m']
            }
        
        return None
    
    async def stream_realtime_bottoms(self, symbol='btcusdt'):
        """
        Stream WebSocket pour détecter les bottoms en temps réel
        """
        url = f"wss://stream.binance.com:9443/ws/{symbol}@trade"
        
        async with websockets.connect(url) as websocket:
            print(f"Connecté au stream {symbol}")
            
            window_trades = []
            window_duration = 60  # Fenêtre glissante de 60 secondes
            
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    trade = {
                        'time': datetime.fromtimestamp(data['T'] / 1000),
                        'price': float(data['p']),
                        'quantity': float(data['q']),
                        'is_buyer': data['m']
                    }
                    
                    window_trades.append(trade)
                    
                    # Nettoyer les vieux trades
                    cutoff_time = datetime.now() - timedelta(seconds=window_duration)
                    window_trades = [t for t in window_trades if t['time'] > cutoff_time]
                    
                    # Détecter si c'est un nouveau minimum
                    if window_trades:
                        prices = [t['price'] for t in window_trades]
                        if trade['price'] == min(prices):
                            print(f"🔴 NOUVEAU BOTTOM DÉTECTÉ: {trade['price']} à {trade['time'].strftime('%H:%M:%S.%f')[:-3]}")
                            
                except Exception as e:
                    print(f"Erreur WebSocket: {e}")
                    break

class CryptoCompareMinuteData:
    """
    Utilise CryptoCompare pour données historiques précises
    """
    
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.base_url = "https://min-api.cryptocompare.com/data/v2"
    
    def get_exact_bottom(self, timestamp, symbol='BTC', currency='USDT'):
        """
        Récupère les données minute par minute autour d'un timestamp
        """
        # Convertir le timestamp en heure Unix
        unix_time = int(timestamp.timestamp())
        
        # Récupérer 240 minutes (4 heures) de données
        url = f"{self.base_url}/histominute"
        params = {
            'fsym': symbol,
            'tsym': currency,
            'limit': 240,
            'toTs': unix_time + 7200,  # +2 heures après le timestamp
            'api_key': self.api_key
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if data['Response'] == 'Success':
                df = pd.DataFrame(data['Data']['Data'])
                df['time'] = pd.to_datetime(df['time'], unit='s')
                df.set_index('time', inplace=True)
                
                # Filtrer la fenêtre de 4 heures
                start = timestamp - timedelta(hours=2)
                end = timestamp + timedelta(hours=2)
                df_window = df[(df.index >= start) & (df.index <= end)]
                
                # Trouver le minimum
                min_idx = df_window['low'].idxmin()
                min_data = df_window.loc[min_idx]
                
                return {
                    'exact_time': min_idx,
                    'exact_price': min_data['low'],
                    'open': min_data['open'],
                    'high': min_data['high'],
                    'close': min_data['close'],
                    'volume': min_data['volumefrom'],
                    'precision': '±1 minute'
                }
        
        return None