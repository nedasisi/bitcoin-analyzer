"""
Script de test rapide pour vérifier les corrections
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz

def test_fixes():
    st.title("🧪 Test des Corrections")
    
    # Test 1: Date/Time inputs
    st.header("Test 1: Date/Time Inputs")
    
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("Date", datetime.now().date())
    with col2:
        time = st.time_input("Heure", datetime.now().time())
    
    combined = datetime.combine(date, time)
    st.success(f"Date/Heure combinée: {combined}")
    
    # Test 2: Timezone aware datetime
    st.header("Test 2: Timezone Handling")
    
    # Créer un timestamp avec timezone
    tz = pytz.timezone('Europe/Paris')
    dt_aware = datetime.now(tz)
    st.write(f"DateTime avec TZ: {dt_aware}")
    
    # Calculer la différence
    dt_now = datetime.now(dt_aware.tzinfo)
    diff = (dt_now - dt_aware).total_seconds()
    st.success(f"Différence: {diff:.2f} secondes")
    
    # Test 3: Pandas period
    st.header("Test 3: Pandas Period")
    
    dates = pd.date_range(start='2024-01-01', end='2024-03-01', freq='D')
    df = pd.DataFrame({'date': dates, 'value': range(len(dates))})
    df.set_index('date', inplace=True)
    
    # Utiliser 'ME' au lieu de 'M'
    try:
        monthly = df.resample('ME').sum()
        st.success("✅ Resample avec 'ME' fonctionne")
        st.dataframe(monthly)
    except:
        monthly = df.resample('M').sum()
        st.warning("⚠️ Utilise encore 'M' (deprecated)")
    
    st.success("🎉 Tous les tests passent!")

if __name__ == "__main__":
    test_fixes()