"""
Configuration pour utiliser des exchanges alternatifs sur Streamlit Cloud
"""

import os
import streamlit as st

# Détection automatique de Streamlit Cloud
IS_CLOUD = (
    os.environ.get('STREAMLIT_RUNTIME_ENV') == 'cloud' or
    'streamlit.app' in os.environ.get('STREAMLIT_URL', '')
)

def get_exchange_config():
    """Retourne la configuration d'exchange appropriée selon l'environnement"""
    
    if IS_CLOUD:
        # Sur Streamlit Cloud, utiliser des exchanges sans restriction US
        st.sidebar.info("☁️ Mode Cloud - Utilisation d'exchanges alternatifs")
        return {
            'primary': 'kucoin',  # KuCoin fonctionne depuis les US
            'fallback': ['bitget', 'bybit', 'mexc'],
            'symbol': 'BTC/USDT',
            'testnet': False
        }
    else:
        # En local, utiliser Binance
        return {
            'primary': 'binance',
            'fallback': ['bitget', 'kucoin'],
            'symbol': 'BTC/USDT', 
            'testnet': False
        }

# Patch pour les méthodes qui utilisent Binance
def patch_data_collector():
    """Modifie le data collector pour utiliser le bon exchange"""
    config = get_exchange_config()
    
    # Stocker la config dans session state
    if 'exchange_config' not in st.session_state:
        st.session_state.exchange_config = config
    
    return config

# Fonction pour obtenir des données depuis n'importe quel exchange disponible
def get_fallback_data(symbol='BTC/USDT', timeframe='4h', limit=500):
    """Essaie plusieurs exchanges jusqu'à obtenir des données"""
    import ccxt
    import pandas as pd
    
    exchanges_to_try = [
        ('kucoin', ccxt.kucoin),
        ('bitget', ccxt.bitget),
        ('bybit', ccxt.bybit),
        ('mexc', ccxt.mexc),
        ('gateio', ccxt.gateio),
    ]
    
    for name, exchange_class in exchanges_to_try:
        try:
            exchange = exchange_class({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
            
            # Tester si l'exchange a le symbole
            markets = exchange.load_markets()
            if symbol not in markets:
                continue
            
            # Récupérer les données
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            # Convertir en DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('datetime', inplace=True)
            
            st.sidebar.success(f"✅ Données depuis {name.upper()}")
            return df
            
        except Exception as e:
            continue
    
    # Si aucun exchange ne marche, retourner None
    st.error("❌ Impossible de récupérer les données depuis aucun exchange")
    return None
