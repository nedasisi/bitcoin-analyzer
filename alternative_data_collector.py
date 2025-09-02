"""
Collecteur de données alternatif pour contourner les restrictions Binance
"""

import ccxt
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import time

class AlternativeDataCollector:
    def __init__(self):
        # Utiliser plusieurs exchanges comme fallback
        self.exchanges = {
            'primary': None,
            'fallback': []
        }
        self.initialize_exchanges()
    
    def initialize_exchanges(self):
        """Initialise les exchanges disponibles"""
        try:
            # Essayer Bitget en premier (pas de restriction US)
            self.exchanges['primary'] = ccxt.bitget({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
            self.exchanges['fallback'].append(self.exchanges['primary'])
        except:
            pass
        
        try:
            # KuCoin comme alternative
            kucoin = ccxt.kucoin({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
            self.exchanges['fallback'].append(kucoin)
        except:
            pass
        
        try:
            # Bybit comme dernière option
            bybit = ccxt.bybit({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
            self.exchanges['fallback'].append(bybit)
        except:
            pass
    
    def fetch_ohlcv_safe(self, symbol='BTC/USDT', timeframe='4h', limit=500):
        """Récupère les données depuis le premier exchange disponible"""
        
        # Essayer chaque exchange jusqu'à ce qu'un fonctionne
        for exchange in self.exchanges['fallback']:
            if exchange is None:
                continue
                
            try:
                # Récupérer les données
                ohlcv = exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=limit
                )
                
                # Convertir en DataFrame
                df = pd.DataFrame(
                    ohlcv,
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                )
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('datetime', inplace=True)
                
                # Ajouter le nom de l'exchange pour info
                st.sidebar.success(f"✅ Données depuis {exchange.id.upper()}")
                
                return df
                
            except Exception as e:
                continue
        
        # Si aucun exchange ne fonctionne, utiliser des données de démonstration
        st.warning("⚠️ Impossible de récupérer les données en temps réel. Utilisation de données de démonstration.")
        return self.get_demo_data()
    
    def get_demo_data(self):
        """Génère des données de démonstration réalistes"""
        import numpy as np
        
        # Créer 500 périodes de données
        dates = pd.date_range(end=datetime.now(), periods=500, freq='4H')
        
        # Générer des prix réalistes
        base_price = 65000
        prices = []
        price = base_price
        
        for i in range(500):
            # Variation aléatoire mais réaliste
            change = np.random.normal(0, 0.02)  # 2% de volatilité
            price = price * (1 + change)
            prices.append(price)
        
        # Créer le DataFrame
        df = pd.DataFrame({
            'open': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'close': [p * 1.005 for p in prices],
            'volume': np.random.uniform(100, 1000, 500)
        }, index=dates)
        
        return df

# Remplacer le data_collector standard
@st.cache_data(ttl=3600)
def get_bitcoin_data(timeframe='4h', limit=500):
    """Fonction wrapper pour récupérer les données Bitcoin"""
    collector = AlternativeDataCollector()
    return collector.fetch_ohlcv_safe(
        symbol='BTC/USDT',
        timeframe=timeframe,
        limit=limit
    )
