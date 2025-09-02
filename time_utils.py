"""
Utilitaires pour améliorer la précision temporelle des bottoms
"""

import pandas as pd
import numpy as np

def estimate_exact_bottom_time(candle_data):
    """
    Estime l'heure exacte du minimum dans une bougie basée sur OHLC
    
    Logique:
    - Si close < open (bougie baissière): Bottom probablement vers la fin (75%)
    - Si |low-open| < |low-close|: Bottom proche de l'open (25%)
    - Sinon: Bottom au milieu (50%)
    """
    open_price = candle_data['open']
    close_price = candle_data['close']
    low_price = candle_data['low']
    timestamp = candle_data.name  # L'index est le timestamp
    
    # Déterminer la position du low dans la bougie
    if close_price < open_price:
        # Bougie baissière - low probablement vers la fin
        offset_ratio = 0.75
    elif abs(low_price - open_price) < abs(low_price - close_price):
        # Low plus proche de l'open
        offset_ratio = 0.25
    else:
        # Low au milieu ou indéterminé
        offset_ratio = 0.5
    
    return offset_ratio

def add_exact_times_to_bottoms(bottoms_df, ohlcv_df, timeframe):
    """
    Ajoute les heures exactes estimées aux bottoms détectés
    """
    if bottoms_df.empty:
        return bottoms_df
    
    bottoms_with_exact = bottoms_df.copy()
    
    # Calculer la durée d'une bougie en secondes
    timeframe_seconds = {
        '5m': 300,
        '15m': 900,
        '30m': 1800,
        '1h': 3600,
        '2h': 7200,
        '4h': 14400,
        '1d': 86400
    }
    
    candle_duration = timeframe_seconds.get(timeframe, 3600)
    
    exact_times = []
    for idx in bottoms_with_exact.index:
        if idx in ohlcv_df.index:
            candle = ohlcv_df.loc[idx]
            offset_ratio = estimate_exact_bottom_time(candle)
            exact_time = idx + pd.Timedelta(seconds=candle_duration * offset_ratio)
            exact_times.append(exact_time)
        else:
            exact_times.append(idx)
    
    bottoms_with_exact['exact_time'] = exact_times
    
    return bottoms_with_exact

def format_time_display(timestamp, exact_time, timezone='UTC'):
    """
    Formate l'affichage du temps avec précision
    """
    if pd.isna(exact_time):
        return timestamp.strftime('%H:%M')
    
    # Afficher l'heure exacte estimée
    exact_str = exact_time.strftime('%H:%M')
    
    # Si différent de l'heure de la bougie, montrer les deux
    candle_hour = timestamp.strftime('%H:%M')
    if exact_str != candle_hour:
        return f"{exact_str} (±{int((exact_time - timestamp).total_seconds() / 60)}min)"
    
    return exact_str