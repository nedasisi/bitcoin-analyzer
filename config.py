"""
Configuration pour l'application Bitcoin Bottom Analyzer
"""

# API Configuration
EXCHANGE = "bitget"
SYMBOL = "BTC/USDT:USDT"  # Format CCXT pour BTCUSDT.P

# Timeframes disponibles
TIMEFRAMES = {
    "5m": "5 minutes",
    "15m": "15 minutes",
    "30m": "30 minutes",
    "1h": "1 heure",
    "2h": "2 heures",
    "4h": "4 heures",
    "1d": "1 jour"
}

# Timeframe par défaut
DEFAULT_TIMEFRAME = "4h"  # Retour à 4h comme avant
TIMEFRAME = DEFAULT_TIMEFRAME
START_DATE = "2019-07-01"

# Paramètres de détection des bottoms (pour 4H)
BOTTOM_PARAMS = {
    "lookback_periods": 30,  # 30*4h = 5 jours
    "min_bounce_percent": 5,  # Rebond minimum pour confirmer (%)
    "volume_threshold": 1.5,  # Volume minimum vs moyenne (1.5x)
    "rsi_oversold": 30,  # RSI pour survente
    "major_bottom_days": 90,  # Jours pour bottom majeur
}

# Multiplicateurs selon le timeframe pour ajuster les paramètres
TIMEFRAME_MULTIPLIERS = {
    "5m": 48,    # 48 * 5min = 4h
    "15m": 16,   # 16 * 15min = 4h
    "30m": 8,    # 8 * 30min = 4h
    "1h": 4,     # 4 * 1h = 4h
    "2h": 2,     # 2 * 2h = 4h
    "4h": 1,     # Base
    "1d": 0.25   # 1/4
}

# Paramètres de cache
USE_CACHE = True
CACHE_EXPIRY_HOURS = 4
CACHE_FILE = "data/btc_history.csv"

# Paramètres Streamlit
PAGE_CONFIG = {
    "page_title": "Bitcoin Bottom Analyzer",
    "page_icon": "📈",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# Sessions de trading (UTC)
TRADING_SESSIONS = {
    "Asia": (0, 8),      # 00:00-08:00 UTC
    "Europe": (8, 16),   # 08:00-16:00 UTC  
    "US": (16, 24)       # 16:00-00:00 UTC
}

# Jours de la semaine
DAYS_FR = {
    0: "Lundi",
    1: "Mardi", 
    2: "Mercredi",
    3: "Jeudi",
    4: "Vendredi",
    5: "Samedi",
    6: "Dimanche"
}