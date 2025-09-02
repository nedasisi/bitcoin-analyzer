"""
Module d'intégration pour afficher l'heure exacte dans le dashboard
"""

import streamlit as st
import pandas as pd
from exact_bottom_finder import ExactBottomFinder
from tick_data_collector import CryptoCompareMinuteData
import time

def add_exact_time_column(bottoms_df, method='1m_data', progress_bar=None):
    """
    Ajoute une colonne avec l'heure exacte des bottoms
    
    Args:
        bottoms_df: DataFrame avec les bottoms détectés
        method: '1m_data', 'tick_data', ou 'cryptocompare'
        progress_bar: Barre de progression Streamlit (optionnel)
    """
    
    if method == '1m_data':
        finder = ExactBottomFinder()
        exact_times = []
        
        total = len(bottoms_df)
        for i, (idx, row) in enumerate(bottoms_df.head(10).iterrows()):  # Limiter à 10 pour demo
            if progress_bar:
                progress_bar.progress((i + 1) / min(total, 10))
                st.text(f"Recherche heure exacte {i+1}/{min(total, 10)}: {idx}")
            
            result = finder.get_exact_bottom_time(idx)
            if result:
                exact_times.append(result['exact_time'])
            else:
                exact_times.append(idx)
            
            time.sleep(0.5)  # Respecter rate limits
        
        # Ajouter NaT pour les bottoms non traités
        while len(exact_times) < len(bottoms_df):
            exact_times.append(pd.NaT)
        
        bottoms_df['exact_time_1m'] = exact_times
    
    elif method == 'cryptocompare':
        cc = CryptoCompareMinuteData()
        exact_times = []
        
        for idx in bottoms_df.index[:5]:  # Limiter pour demo
            result = cc.get_exact_bottom(idx)
            if result:
                exact_times.append(result['exact_time'])
            else:
                exact_times.append(idx)
        
        while len(exact_times) < len(bottoms_df):
            exact_times.append(pd.NaT)
        
        bottoms_df['exact_time_cc'] = exact_times
    
    return bottoms_df

def display_exact_time_analysis(bottoms_df, selected_tz_name):
    """
    Affiche une analyse détaillée de l'heure exacte des bottoms
    """
    st.header(f"🎯 Analyse Heure Exacte des Bottoms ({selected_tz_name})")
    
    # Options de méthode
    col1, col2 = st.columns(2)
    
    with col1:
        method = st.selectbox(
            "Méthode de calcul",
            ["Estimation OHLC (rapide)", "Données 1 minute (précis)", "CryptoCompare API (très précis)"]
        )
    
    with col2:
        if st.button("🔍 Calculer Heures Exactes"):
            with st.spinner("Récupération des données précises..."):
                progress = st.progress(0)
                
                if "1 minute" in method:
                    bottoms_df = add_exact_time_column(bottoms_df, '1m_data', progress)
                elif "CryptoCompare" in method:
                    bottoms_df = add_exact_time_column(bottoms_df, 'cryptocompare', progress)
                
                st.success("✅ Heures exactes calculées!")
    
    # Tableau comparatif
    if 'exact_time_1m' in bottoms_df.columns or 'exact_time_cc' in bottoms_df.columns:
        st.subheader("📊 Comparaison des Heures")
        
        comparison_df = pd.DataFrame({
            'Date': bottoms_df.index.strftime('%Y-%m-%d'),
            'Heure Bougie': bottoms_df.index.strftime('%H:%M'),
            'Heure Estimée OHLC': bottoms_df['exact_time'].dt.strftime('%H:%M:%S') if 'exact_time' in bottoms_df.columns else 'N/A',
            'Heure Exacte 1m': bottoms_df['exact_time_1m'].dt.strftime('%H:%M:%S') if 'exact_time_1m' in bottoms_df.columns else 'N/A',
            'Prix': bottoms_df['price'].apply(lambda x: f"${x:,.0f}")
        })
        
        # Calculer la différence
        if 'exact_time_1m' in bottoms_df.columns:
            diff_minutes = (bottoms_df['exact_time_1m'] - bottoms_df.index).dt.total_seconds() / 60
            comparison_df['Écart (min)'] = diff_minutes.apply(lambda x: f"{x:.0f}" if pd.notna(x) else 'N/A')
        
        st.dataframe(comparison_df.head(10), use_container_width=True)
        
        # Graphique de distribution des écarts
        if 'exact_time_1m' in bottoms_df.columns:
            st.subheader("📈 Distribution des Écarts Temporels")
            
            valid_diffs = diff_minutes.dropna()
            if not valid_diffs.empty:
                import plotly.express as px
                
                fig = px.histogram(
                    valid_diffs,
                    nbins=20,
                    title="Distribution des écarts entre heure de bougie et heure exacte",
                    labels={'value': 'Écart (minutes)', 'count': 'Nombre de bottoms'}
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Statistiques
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Écart Moyen", f"{valid_diffs.mean():.1f} min")
                with col2:
                    st.metric("Écart Médian", f"{valid_diffs.median():.1f} min")
                with col3:
                    st.metric("Écart Max", f"{valid_diffs.abs().max():.1f} min")

def create_exact_time_dashboard_tab():
    """
    Crée un onglet dédié à l'analyse de l'heure exacte
    """
    return {
        'title': '🎯 Heure Exacte',
        'function': display_exact_time_analysis
    }