"""
Dashboard Principal Amélioré - Bitcoin Analyzer
Organisation claire avec sections dédiées Bottoms et Tops
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np
import pytz
import time

from config import *
from data_collector import DataCollector
from bottom_analyzer import BottomAnalyzer
from top_analyzer import TopAnalyzer
from time_utils import add_exact_times_to_bottoms, format_time_display
from display_utils import display_bottoms_with_exact_time
from exact_bottom_finder import ExactBottomFinder
from exact_top_finder import ExactTopFinder
from batch_analyzer import BatchExactTimeAnalyzer
from temporal_analysis import create_temporal_analysis_tab
from advanced_dashboard import create_advanced_analysis_tab
from enhanced_exact_time_tab import display_exact_time_tab_with_full_analysis
from tops_dashboard import create_tops_analysis_tab

# Configuration de la page
st.set_page_config(
    page_title="Bitcoin Analyzer Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé amélioré
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 2rem;
        font-weight: bold;
        color: #2ca02c;
        border-bottom: 3px solid #2ca02c;
        padding-bottom: 10px;
        margin: 20px 0;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .plot-container {
        border: 1px solid #e0e0e0;
        border-radius: 5px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Fonction pour charger les données (cache)
@st.cache_data(ttl=3600)
def load_data(timeframe="4h"):
    """Charge les données avec cache de 1h"""
    with st.spinner(f"Chargement des données en {timeframe}..."):
        collector = DataCollector()
        import config
        config.TIMEFRAME = timeframe
        df = collector.get_historical_data()
        
        if df is not None and not df.empty:
            df = collector.add_technical_indicators(df)
            df = collector.estimate_liquidations(df)
            return df
        return None

def main():
    """Fonction principale du dashboard"""
    
    # Titre principal
    st.markdown('<h1 class="main-header">🔍 Bitcoin Analyzer Pro - BTCUSDT.P</h1>', unsafe_allow_html=True)
    st.markdown("*Analyse complète des Bottoms & Tops depuis 2019*")
    
    # Sidebar pour configuration globale
    with st.sidebar:
        st.header("⚙️ Configuration Globale")
        
        # Fuseau horaire
        st.subheader("🌍 Fuseau Horaire")
        timezone_options = {
            "UTC": "UTC",
            "New York 🇺🇸": "America/New_York",
            "Paris 🇫🇷": "Europe/Paris",
            "Bangkok 🇹🇭": "Asia/Bangkok"
        }
        
        selected_tz_name = st.selectbox(
            "Choisir le fuseau horaire",
            list(timezone_options.keys()),
            index=2,  # Paris par défaut
            help="Toutes les heures seront converties dans ce fuseau"
        )
        selected_tz = timezone_options[selected_tz_name]
        
        # Heure actuelle
        tz_obj = pytz.timezone(selected_tz)
        current_time = datetime.now(tz_obj)
        st.caption(f"🕒 Heure actuelle : {current_time.strftime('%H:%M')} ({selected_tz_name})")
        
        st.markdown("---")
        
        # Timeframe
        st.subheader("⏱️ Timeframe")
        selected_timeframe = st.selectbox(
            "Choisir le timeframe",
            list(TIMEFRAMES.keys()),
            index=list(TIMEFRAMES.keys()).index(DEFAULT_TIMEFRAME),
            help="4h recommandé pour l'analyse"
        )
        
        st.markdown("---")
        
        # Période d'analyse
        st.subheader("📅 Période")
        date_range = st.date_input(
            "Période d'analyse",
            value=(datetime(2019, 7, 1), datetime.now()),
            min_value=datetime(2019, 7, 1),
            max_value=datetime.now()
        )
        
        st.markdown("---")
        
        # Mode d'affichage
        st.subheader("🎨 Mode d'Affichage")
        display_mode = st.radio(
            "Choisir la vue",
            ["📊 Vue Combinée", "📉 Bottoms Only", "📈 Tops Only"],
            index=0,
            help="Sélectionner ce que vous voulez analyser"
        )
        
        # Bouton refresh
        if st.button("🔄 Actualiser les données", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Chargement des données
    df = load_data(selected_timeframe)
    
    if df is None:
        st.error("❌ Impossible de charger les données. Vérifiez votre connexion.")
        return
    
    # Filtrer par date
    if len(date_range) == 2:
        mask = (df.index >= pd.Timestamp(date_range[0])) & (df.index <= pd.Timestamp(date_range[1]))
        df_filtered = df.loc[mask]
    else:
        df_filtered = df
    
    # Analyser les bottoms et tops
    bottom_analyzer = BottomAnalyzer(df_filtered)
    top_analyzer = TopAnalyzer(df_filtered)
    
    bottoms = bottom_analyzer.detect_bottoms(method='all')
    tops = top_analyzer.detect_tops(method='all')
    
    # Convertir au fuseau horaire
    if selected_tz != "UTC":
        if not bottoms.empty:
            if not bottoms.index.tz:
                bottoms.index = bottoms.index.tz_localize('UTC')
            bottoms.index = bottoms.index.tz_convert(selected_tz)
            bottoms['hour'] = bottoms.index.hour
            bottoms['day_of_week'] = bottoms.index.dayofweek
        
        if not tops.empty:
            if not tops.index.tz:
                tops.index = tops.index.tz_localize('UTC')
            tops.index = tops.index.tz_convert(selected_tz)
            tops['hour'] = tops.index.hour
            tops['day_of_week'] = tops.index.dayofweek
    
    # Affichage selon le mode sélectionné
    if display_mode == "📊 Vue Combinée":
        display_combined_view(df_filtered, bottoms, tops, selected_tz_name, selected_tz, selected_timeframe)
    elif display_mode == "📉 Bottoms Only":
        display_bottoms_section(df_filtered, bottoms, selected_tz_name, selected_tz, selected_timeframe)
    elif display_mode == "📈 Tops Only":
        display_tops_section(df_filtered, tops, selected_tz_name, selected_tz, selected_timeframe)
    
    # Footer
    st.markdown("---")
    st.markdown(f"""
    <div style='text-align: center; color: gray;'>
        <small>
        Bitcoin Analyzer Pro v2.0 | Données: BTCUSDT.P depuis 2019<br>
        Fuseau: {selected_tz_name} | Timeframe: {selected_timeframe}<br>
        ⚠️ Ceci n'est pas un conseil financier. Tradez à vos risques et périls.
        </small>
    </div>
    """, unsafe_allow_html=True)

def display_combined_view(df, bottoms, tops, tz_name, tz, timeframe):
    """Affiche la vue combinée avec bottoms et tops"""
    
    # Métriques générales
    st.markdown('<h2 class="section-header">📊 Vue d\'Ensemble Globale</h2>', unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Prix Actuel", f"${df['close'].iloc[-1]:,.0f}")
    
    with col2:
        st.metric("Total Bottoms", len(bottoms))
    
    with col3:
        st.metric("Total Tops", len(tops))
    
    with col4:
        ratio = len(tops) / len(bottoms) if len(bottoms) > 0 else 0
        st.metric("Ratio T/B", f"{ratio:.2f}")
    
    with col5:
        volatility = df['close'].pct_change().std() * 100
        st.metric("Volatilité", f"{volatility:.1f}%")
    
    # Graphique principal combiné
    st.subheader("📈 Graphique Prix avec Bottoms & Tops")
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=("Prix BTC/USDT", "Volume")
    )
    
    # Chandelier
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name="BTC",
            showlegend=False
        ),
        row=1, col=1
    )
    
    # Marquer les bottoms
    if not bottoms.empty:
        for bottom_type in ['major', 'confirmed', 'simple']:
            if 'type' in bottoms.columns:
                type_bottoms = bottoms[bottoms['type'] == bottom_type]
            else:
                type_bottoms = bottoms if bottom_type == 'simple' else pd.DataFrame()
            
            if not type_bottoms.empty:
                colors = {'simple': 'yellow', 'confirmed': 'orange', 'major': 'red'}
                fig.add_trace(
                    go.Scatter(
                        x=type_bottoms.index,
                        y=type_bottoms['price'],
                        mode='markers',
                        marker=dict(
                            size=10,
                            color=colors.get(bottom_type, 'blue'),
                            symbol='triangle-up'
                        ),
                        name=f"Bottom {bottom_type}"
                    ),
                    row=1, col=1
                )
    
    # Marquer les tops
    if not tops.empty:
        for top_type in ['major', 'confirmed', 'simple']:
            if 'type' in tops.columns:
                type_tops = tops[tops['type'] == top_type]
            else:
                type_tops = tops if top_type == 'simple' else pd.DataFrame()
            
            if not type_tops.empty:
                colors = {'simple': 'lightgreen', 'confirmed': 'green', 'major': 'darkgreen'}
                fig.add_trace(
                    go.Scatter(
                        x=type_tops.index,
                        y=type_tops['price'],
                        mode='markers',
                        marker=dict(
                            size=10,
                            color=colors.get(top_type, 'green'),
                            symbol='triangle-down'
                        ),
                        name=f"Top {top_type}"
                    ),
                    row=1, col=1
                )
    
    # Volume
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['volume'],
            name="Volume",
            marker_color='lightblue',
            showlegend=False
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        height=700,
        xaxis_rangeslider_visible=False,
        title=f"Vue Combinée Bottoms & Tops ({tz_name})"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Sections séparées
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📉 Section Bottoms")
        display_bottoms_summary(bottoms, tz_name)
    
    with col2:
        st.markdown("### 📈 Section Tops")
        display_tops_summary(tops, tz_name)
    
    # Comparaison temporelle
    st.markdown('<h2 class="section-header">⏰ Analyse Temporelle Comparée</h2>', unsafe_allow_html=True)
    display_temporal_comparison(bottoms, tops, tz_name)

def display_bottoms_section(df, bottoms, tz_name, tz, timeframe):
    """Section dédiée aux bottoms"""
    
    st.markdown('<h2 class="section-header">📉 Analyse des Bottoms</h2>', unsafe_allow_html=True)
    
    # Sous-onglets pour les bottoms
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎯 Vue d'ensemble",
        "📊 Patterns",
        "⏰ Analyse Temporelle", 
        "💰 Backtest",
        "🎯 Heure Exacte"
    ])
    
    with tab1:
        display_bottoms_overview(bottoms, df, tz_name)
    
    with tab2:
        display_bottoms_patterns(bottoms, tz_name)
    
    with tab3:
        from temporal_analysis import create_temporal_analysis_tab
        analyzer = BottomAnalyzer(df)
        analyzer.bottoms = bottoms
        patterns = analyzer.analyze_patterns()
        DAYS_FR = {0: 'Lundi', 1: 'Mardi', 2: 'Mercredi', 3: 'Jeudi', 4: 'Vendredi', 5: 'Samedi', 6: 'Dimanche'}
        create_temporal_analysis_tab(bottoms, tz_name, patterns, DAYS_FR)
    
    with tab4:
        display_bottoms_backtest(bottoms, df, tz_name)
    
    with tab5:
        display_exact_time_tab_with_full_analysis(bottoms, tz, tz_name, timeframe)

def display_tops_section(df, tops, tz_name, tz, timeframe):
    """Section dédiée aux tops"""
    
    st.markdown('<h2 class="section-header">📈 Analyse des Tops</h2>', unsafe_allow_html=True)
    
    # Utiliser la fonction existante
    create_tops_analysis_tab(df, tz_name, tz)

def display_bottoms_summary(bottoms, tz_name):
    """Résumé des bottoms pour la vue combinée"""
    
    if bottoms.empty:
        st.warning("Aucun bottom détecté")
        return
    
    # Métriques
    col1, col2 = st.columns(2)
    
    with col1:
        if 'type' in bottoms.columns:
            major_count = len(bottoms[bottoms['type'] == 'major'])
            st.metric("Bottoms Majeurs", major_count)
    
    with col2:
        avg_bounce = bottoms['bounce_pct'].mean() if 'bounce_pct' in bottoms.columns else 0
        st.metric("Rebond Moyen", f"{avg_bounce:.1f}%")
    
    # Top 5 bottoms récents
    st.markdown("**Bottoms Récents:**")
    recent = bottoms.sort_index(ascending=False).head(5)
    for idx, row in recent.iterrows():
        st.text(f"• {idx.strftime('%Y-%m-%d %H:%M')} - ${row['price']:,.0f}")

def display_tops_summary(tops, tz_name):
    """Résumé des tops pour la vue combinée"""
    
    if tops.empty:
        st.warning("Aucun top détecté")
        return
    
    # Métriques
    col1, col2 = st.columns(2)
    
    with col1:
        if 'type' in tops.columns:
            major_count = len(tops[tops['type'] == 'major'])
            st.metric("Tops Majeurs", major_count)
    
    with col2:
        avg_drop = tops['drop_pct'].mean() if 'drop_pct' in tops.columns else 0
        st.metric("Chute Moyenne", f"{avg_drop:.1f}%")
    
    # Top 5 tops récents
    st.markdown("**Tops Récents:**")
    recent = tops.sort_index(ascending=False).head(5)
    for idx, row in recent.iterrows():
        st.text(f"• {idx.strftime('%Y-%m-%d %H:%M')} - ${row['price']:,.0f}")

def display_temporal_comparison(bottoms, tops, tz_name):
    """Compare les patterns temporels des bottoms et tops"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Distribution horaire
        if not bottoms.empty and not tops.empty:
            hourly_bottoms = bottoms.groupby('hour').size()
            hourly_tops = tops.groupby('hour').size()
            
            all_hours = list(range(24))
            
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=[f"{h:02d}:00" for h in all_hours],
                y=[hourly_bottoms.get(h, 0) for h in all_hours],
                name='Bottoms',
                marker_color='red'
            ))
            
            fig.add_trace(go.Bar(
                x=[f"{h:02d}:00" for h in all_hours],
                y=[hourly_tops.get(h, 0) for h in all_hours],
                name='Tops',
                marker_color='green'
            ))
            
            fig.update_layout(
                title=f"Distribution Horaire ({tz_name})",
                xaxis_title="Heure",
                yaxis_title="Nombre",
                barmode='group',
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Statistiques comparatives
        st.markdown("### 📊 Statistiques Comparatives")
        
        if not bottoms.empty and not tops.empty:
            DAYS_FR = {0: 'Lundi', 1: 'Mardi', 2: 'Mercredi', 3: 'Jeudi', 4: 'Vendredi', 5: 'Samedi', 6: 'Dimanche'}
            
            stats_df = pd.DataFrame({
                'Métrique': [
                    'Total',
                    'Heure la plus fréquente',
                    'Jour le plus fréquent',
                    'Type majeur'
                ],
                'Bottoms': [
                    len(bottoms),
                    f"{int(bottoms.groupby('hour').size().idxmax()):02d}:00",
                    DAYS_FR[bottoms.groupby('day_of_week').size().idxmax()],
                    len(bottoms[bottoms['type'] == 'major']) if 'type' in bottoms.columns else 'N/A'
                ],
                'Tops': [
                    len(tops),
                    f"{int(tops.groupby('hour').size().idxmax()):02d}:00",
                    DAYS_FR[tops.groupby('day_of_week').size().idxmax()],
                    len(tops[tops['type'] == 'major']) if 'type' in tops.columns else 'N/A'
                ]
            })
            
            st.dataframe(stats_df, use_container_width=True, hide_index=True)

def display_bottoms_overview(bottoms, df, tz_name):
    """Vue d'ensemble détaillée des bottoms"""
    # Implémenter la vue d'ensemble des bottoms
    st.info("Vue d'ensemble des bottoms")

def display_bottoms_patterns(bottoms, tz_name):
    """Analyse des patterns des bottoms"""
    # Implémenter l'analyse des patterns
    st.info("Patterns des bottoms")

def display_bottoms_backtest(bottoms, df, tz_name):
    """Backtest des stratégies sur les bottoms"""
    # Implémenter le backtest
    st.info("Backtest des stratégies bottoms")

if __name__ == "__main__":
    main()