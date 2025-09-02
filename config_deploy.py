"""
Configuration sécurisée pour le déploiement
"""

import streamlit as st
import os

# Mode de déploiement
IS_DEPLOYED = os.environ.get('STREAMLIT_RUNTIME_ENV') == 'cloud'

# Configuration API
if IS_DEPLOYED:
    # En production : utiliser les secrets Streamlit
    try:
        API_CONFIG = {
            'binance_key': st.secrets.get("api", {}).get("binance_key", ""),
            'binance_secret': st.secrets.get("api", {}).get("binance_secret", ""),
            'use_testnet': False
        }
    except:
        API_CONFIG = {
            'binance_key': "",
            'binance_secret': "",
            'use_testnet': True
        }
else:
    # En local : utiliser les variables d'environnement ou valeurs par défaut
    API_CONFIG = {
        'binance_key': os.environ.get('BINANCE_KEY', ''),
        'binance_secret': os.environ.get('BINANCE_SECRET', ''),
        'use_testnet': True
    }

# Timeframes disponibles
TIMEFRAMES = {
    '1h': '1h',
    '4h': '4h',
    '1d': '1d'
}

# Paramètres par défaut
DEFAULT_TIMEFRAME = '4h'
DEFAULT_TIMEZONE = 'Europe/Paris'

# Limites pour éviter surcharge
MAX_DAYS_HISTORY = 365 * 3  # 3 ans max en production
MAX_BOTTOMS_ANALYZE = 20    # Max bottoms pour analyse exacte
CACHE_TTL = 3600            # 1 heure de cache

# Paramètres d'analyse
BOTTOM_PARAMS = {
    'lookback_periods': 30,
    'min_bounce_percent': 5,
    'volume_threshold': 1.5,
    'rsi_oversold': 30,
    'rsi_period': 14
}

TOP_PARAMS = {
    'lookback_periods': 30,
    'min_drop_percent': 5,
    'volume_threshold': 1.5,
    'rsi_overbought': 70,
    'rsi_period': 14
}

# Jours de la semaine en français
DAYS_FR = {
    0: 'Lundi',
    1: 'Mardi', 
    2: 'Mercredi',
    3: 'Jeudi',
    4: 'Vendredi',
    5: 'Samedi',
    6: 'Dimanche'
}

# Configuration de la page Streamlit
PAGE_CONFIG = {
    'page_title': 'Bitcoin Analyzer Pro',
    'page_icon': '📊',
    'layout': 'wide',
    'initial_sidebar_state': 'expanded'
}

# Timeframe multipliers pour ajustement des paramètres
TIMEFRAME_MULTIPLIERS = {
    '1h': 4,
    '4h': 1,
    '1d': 0.25
}

# Configuration pour le déploiement
DEPLOYMENT_CONFIG = {
    'enable_api_calls': not IS_DEPLOYED,  # Désactiver les API calls en production
    'use_cached_data': IS_DEPLOYED,       # Utiliser le cache en production
    'max_api_calls_per_hour': 100,        # Limite d'API calls
    'enable_screenshots': not IS_DEPLOYED, # Désactiver screenshots en production
    'data_retention_days': 30             # Garder les données 30 jours
}