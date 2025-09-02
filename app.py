"""
Dashboard Complet Bitcoin Analyzer - Version Complète
Avec TOUS les onglets pour Bottoms ET Tops
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
# Détecter si on est en production
import os
IS_PRODUCTION = os.environ.get('STREAMLIT_RUNTIME_ENV') == 'cloud'

if IS_PRODUCTION:
    # En production : utiliser la version allégée
    from data_collector_prod import DataCollector
else:
    # En local : utiliser la version complète
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
from advanced_tops_scoring import create_advanced_tops_scoring_tab
from gpt5_tops_scoring import create_gpt5_tops_scoring_interface
from trading_journal import create_trading_journal_interface

# Import optionnel de l'authentification
try:
    from auth import check_password
except:
    def check_password():
        return True

# Configuration de la page
st.set_page_config(
    page_title="Bitcoin Analyzer Pro - Complete",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(90deg, #FF6B6B 0%, #4ECDC4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.8rem;
        font-weight: bold;
        padding: 10px;
        border-radius: 5px;
        margin: 20px 0;
    }
    .bottoms-section {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
    }
    .tops-section {
        background-color: #e8f5e9;
        border-left: 4px solid #4caf50;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Fonction de conversion timezone
def convert_to_timezone(df_data, timezone_str):
    """Convertit les données dans le fuseau horaire sélectionné"""
    if df_data.empty or timezone_str == "UTC":
        return df_data
    
    df_converted = df_data.copy()
    
    if not df_converted.index.tz:
        df_converted.index = df_converted.index.tz_localize('UTC')
    
    df_converted.index = df_converted.index.tz_convert(timezone_str)
    
    if 'exact_time' in df_converted.columns:
        df_converted['exact_time'] = pd.to_datetime(df_converted['exact_time'])
        if not df_converted['exact_time'].dt.tz:
            df_converted['exact_time'] = df_converted['exact_time'].dt.tz_localize('UTC')
        df_converted['exact_time'] = df_converted['exact_time'].dt.tz_convert(timezone_str)
    
    df_converted['hour'] = df_converted.index.hour
    df_converted['day_of_week'] = df_converted.index.dayofweek
    
    return df_converted

# Fonction de chargement des données
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

# Fonction d'analyse des bottoms
@st.cache_data(ttl=1800)
def analyze_bottoms(df, bottom_type, lookback, min_bounce, volume_threshold):
    """Analyse les bottoms avec cache de 30min"""
    BOTTOM_PARAMS['lookback_periods'] = lookback
    BOTTOM_PARAMS['min_bounce_percent'] = min_bounce
    BOTTOM_PARAMS['volume_threshold'] = volume_threshold
    
    analyzer = BottomAnalyzer(df)
    
    if bottom_type == "Simples":
        bottoms = analyzer.detect_simple_bottoms()
    elif bottom_type == "Confirmés":
        bottoms = analyzer.detect_confirmed_bottoms()
    elif bottom_type == "Majeurs":
        bottoms = analyzer.detect_major_bottoms()
    else:
        bottoms = analyzer.detect_bottoms(method='all')
    
    analyzer.bottoms = bottoms
    patterns = analyzer.analyze_patterns()
    
    return bottoms, patterns, analyzer

def main():
    """Fonction principale du dashboard complet"""
    
    # Vérifier l'authentification si en production
    if not check_password():
        st.stop()
    
    # Titre principal
    st.markdown('<h1 class="main-header">🔍 Bitcoin Analyzer Pro - Complete Edition</h1>', unsafe_allow_html=True)
    st.markdown("*Analyse complète des Bottoms & Tops avec tous les outils avancés*")
    
    # Sidebar pour configuration
    with st.sidebar:
        st.header("⚙️ Configuration Globale")
        
        # Mode d'analyse principal
        st.subheader("🎯 Mode d'Analyse")
        analysis_mode = st.radio(
            "Que voulez-vous analyser ?",
            ["📉 BOTTOMS (Creux)", "📈 TOPS (Sommets)", "🔄 COMPARAISON", "📓 JOURNAL TRADING"],
            index=0
        )
        
        st.markdown("---")
        
        # Fuseau horaire
        st.subheader("🌍 Fuseau Horaire")
        timezone_options = {
            "UTC": "UTC",
            "New York 🇺🇸": "America/New_York",
            "Paris 🇫🇷": "Europe/Paris",
            "Bangkok 🇹🇭": "Asia/Bangkok"
        }
        
        selected_tz_name = st.selectbox(
            "Fuseau horaire",
            list(timezone_options.keys()),
            index=2  # Paris par défaut
        )
        selected_tz = timezone_options[selected_tz_name]
        
        tz_obj = pytz.timezone(selected_tz)
        current_time = datetime.now(tz_obj)
        st.caption(f"🕒 {current_time.strftime('%H:%M')} ({selected_tz_name})")
        
        st.markdown("---")
        
        # Timeframe
        st.subheader("⏱️ Timeframe")
        selected_timeframe = st.selectbox(
            "Période des bougies",
            list(TIMEFRAMES.keys()),
            index=list(TIMEFRAMES.keys()).index(DEFAULT_TIMEFRAME)
        )
        
        multiplier = TIMEFRAME_MULTIPLIERS.get(selected_timeframe, 1)
        adjusted_lookback = int(BOTTOM_PARAMS['lookback_periods'] * multiplier)
        
        st.markdown("---")
        
        # Type de détection (pour bottoms)
        if analysis_mode == "📉 BOTTOMS (Creux)":
            st.subheader("🎯 Type de Bottoms")
            bottom_type = st.selectbox(
                "Type à détecter",
                ["Tous", "Simples", "Confirmés", "Majeurs"]
            )
        else:
            bottom_type = "Tous"
        
        # Période d'analyse
        st.subheader("📅 Période")
        date_range = st.date_input(
            "Période d'analyse",
            value=(datetime(2019, 7, 1), datetime.now()),
            min_value=datetime(2019, 7, 1),
            max_value=datetime.now()
        )
        
        # Paramètres avancés
        with st.expander("⚙️ Paramètres avancés"):
            lookback = st.slider(
                "Périodes de lookback",
                min_value=10,
                max_value=500,
                value=adjusted_lookback
            )
            
            min_bounce = st.slider(
                "Rebond minimum (%)",
                min_value=1,
                max_value=20,
                value=BOTTOM_PARAMS['min_bounce_percent']
            )
            
            volume_threshold = st.slider(
                "Seuil de volume (x)",
                min_value=1.0,
                max_value=5.0,
                value=BOTTOM_PARAMS['volume_threshold'],
                step=0.5
            )
        
        # Bouton refresh
        if st.button("🔄 Actualiser", use_container_width=True):
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
    
    # Affichage selon le mode sélectionné
    if analysis_mode == "📉 BOTTOMS (Creux)":
        display_bottoms_complete(df_filtered, bottom_type, lookback, min_bounce, volume_threshold, 
                                selected_tz, selected_tz_name, selected_timeframe)
    
    elif analysis_mode == "📈 TOPS (Sommets)":
        display_tops_complete(df_filtered, selected_tz, selected_tz_name, selected_timeframe)
    
    elif analysis_mode == "🔄 COMPARAISON":
        display_comparison_complete(df_filtered, bottom_type, lookback, min_bounce, volume_threshold,
                                   selected_tz, selected_tz_name, selected_timeframe)
    
    elif analysis_mode == "📓 JOURNAL TRADING":
        create_trading_journal_interface(selected_tz_name)
    
    # Footer
    st.markdown("---")
    st.markdown(f"""
    <div style='text-align: center; color: gray;'>
        <small>
        Bitcoin Analyzer Pro - Complete Edition v3.0<br>
        Données: BTCUSDT.P | Fuseau: {selected_tz_name} | Timeframe: {selected_timeframe}<br>
        ⚠️ Ceci n'est pas un conseil financier.
        </small>
    </div>
    """, unsafe_allow_html=True)

def display_bottoms_complete(df, bottom_type, lookback, min_bounce, volume_threshold, 
                            selected_tz, selected_tz_name, selected_timeframe):
    """Affichage complet pour les BOTTOMS avec TOUS les onglets"""
    
    st.markdown('<h2 class="section-header bottoms-section">📉 Analyse Complète des BOTTOMS</h2>', 
                unsafe_allow_html=True)
    
    # Analyser les bottoms
    bottoms, patterns, analyzer = analyze_bottoms(
        df, bottom_type, lookback, min_bounce, volume_threshold
    )
    
    # Ajouter les heures exactes estimées
    if not bottoms.empty:
        bottoms = add_exact_times_to_bottoms(bottoms, df, selected_timeframe)
    
    # Convertir au fuseau horaire
    bottoms_tz = convert_to_timezone(bottoms, selected_tz)
    
    # Réanalyser les patterns avec les nouvelles heures
    if not bottoms_tz.empty:
        analyzer.bottoms = bottoms_tz
        patterns = analyzer.analyze_patterns()
    
    # TOUS LES ONGLETS POUR BOTTOMS (comme dans l'ancien dashboard)
    tabs = st.tabs([
        "📊 Vue d'ensemble",
        "📈 Graphiques",
        "🎯 Patterns",
        "💰 Backtest",
        "📋 Liste Détaillée",
        "⏰ Analyse Temporelle",
        "🎯 Heure Exacte (1min)",
        "🎯 Scoring Avancé",
        "❓ FAQ & Tips"
    ])
    
    with tabs[0]:  # Vue d'ensemble
        display_bottoms_overview(bottoms_tz, patterns, df, selected_tz_name)
    
    with tabs[1]:  # Graphiques
        display_bottoms_charts(df, bottoms_tz, selected_tz_name)
    
    with tabs[2]:  # Patterns
        display_bottoms_patterns(bottoms_tz, patterns, selected_tz_name)
    
    with tabs[3]:  # Backtest
        display_bottoms_backtest(analyzer, patterns, selected_tz_name)
    
    with tabs[4]:  # Liste Détaillée
        display_bottoms_with_exact_time(bottoms_tz, selected_tz_name, selected_timeframe, TIMEFRAMES, DAYS_FR)
    
    with tabs[5]:  # Analyse Temporelle
        create_temporal_analysis_tab(bottoms_tz, selected_tz_name, patterns, DAYS_FR)
    
    with tabs[6]:  # Heure Exacte
        display_exact_time_tab_with_full_analysis(bottoms_tz, selected_tz, selected_tz_name, selected_timeframe)
    
    with tabs[7]:  # Scoring Avancé
        create_advanced_analysis_tab(df, selected_tz_name)
    
    with tabs[8]:  # FAQ
        display_faq_bottoms()

def display_tops_complete(df, selected_tz, selected_tz_name, selected_timeframe):
    """Affichage complet pour les TOPS avec TOUS les onglets"""
    
    st.markdown('<h2 class="section-header tops-section">📈 Analyse Complète des TOPS</h2>', 
                unsafe_allow_html=True)
    
    # Analyser les tops
    analyzer = TopAnalyzer(df)
    tops = analyzer.detect_tops(method='all')
    
    # Convertir au fuseau horaire
    tops_tz = convert_to_timezone(tops, selected_tz)
    
    # Patterns
    if not tops_tz.empty:
        patterns = analyzer.analyze_patterns()
    else:
        patterns = {}
    
    # TOUS LES ONGLETS POUR TOPS (miroir des bottoms)
    tabs = st.tabs([
        "📊 Vue d'ensemble",
        "📈 Graphiques",
        "🎯 Patterns",
        "💰 Backtest Short",
        "📋 Liste Détaillée",
        "⏰ Analyse Temporelle",
        "🎯 Heure Exacte (1min)",
        "🎯 Scoring Avancé",
        "❓ FAQ & Tips"
    ])
    
    with tabs[0]:  # Vue d'ensemble
        display_tops_overview_complete(tops_tz, patterns, df, selected_tz_name)
    
    with tabs[1]:  # Graphiques
        display_tops_charts_complete(df, tops_tz, analyzer, selected_tz_name)
    
    with tabs[2]:  # Patterns
        display_tops_patterns_complete(tops_tz, patterns, selected_tz_name)
    
    with tabs[3]:  # Backtest Short
        display_tops_backtest(analyzer, tops_tz, patterns, selected_tz_name)
    
    with tabs[4]:  # Liste Détaillée
        display_tops_detailed_list(tops_tz, selected_tz_name, selected_timeframe)
    
    with tabs[5]:  # Analyse Temporelle
        display_tops_temporal_complete(tops_tz, patterns, selected_tz_name)
    
    with tabs[6]:  # Heure Exacte
        display_tops_exact_time(tops_tz, selected_tz, selected_tz_name, selected_timeframe)
    
    with tabs[7]:  # Scoring Avancé
        display_tops_advanced_scoring(df, tops_tz, selected_tz_name)
    
    with tabs[8]:  # FAQ
        display_faq_tops()

def display_comparison_complete(df, bottom_type, lookback, min_bounce, volume_threshold,
                               selected_tz, selected_tz_name, selected_timeframe):
    """Comparaison complète Bottoms vs Tops"""
    
    st.markdown('<h2 class="section-header">🔄 Comparaison BOTTOMS vs TOPS</h2>', 
                unsafe_allow_html=True)
    
    # Analyser les deux
    bottoms, patterns_b, analyzer_b = analyze_bottoms(
        df, bottom_type, lookback, min_bounce, volume_threshold
    )
    
    analyzer_t = TopAnalyzer(df)
    tops = analyzer_t.detect_tops(method='all')
    
    # Convertir
    bottoms_tz = convert_to_timezone(bottoms, selected_tz)
    tops_tz = convert_to_timezone(tops, selected_tz)
    
    # Onglets de comparaison
    tabs = st.tabs([
        "📊 Vue Combinée",
        "📈 Graphique Comparé",
        "⏰ Analyse Temporelle",
        "📊 Statistiques",
        "💡 Insights"
    ])
    
    with tabs[0]:
        display_combined_overview(bottoms_tz, tops_tz, df, selected_tz_name)
    
    with tabs[1]:
        display_combined_chart(df, bottoms_tz, tops_tz, selected_tz_name)
    
    with tabs[2]:
        display_temporal_comparison(bottoms_tz, tops_tz, selected_tz_name)
    
    with tabs[3]:
        display_statistics_comparison(bottoms_tz, tops_tz, selected_tz_name)
    
    with tabs[4]:
        display_insights_comparison(bottoms_tz, tops_tz, selected_tz_name)

# --- FONCTIONS D'AFFICHAGE POUR BOTTOMS ---

def display_bottoms_overview(bottoms, patterns, df, tz_name):
    """Vue d'ensemble des bottoms"""
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Bottoms", len(bottoms))
        if 'type' in bottoms.columns:
            major = len(bottoms[bottoms['type'] == 'major'])
            st.metric("Majeurs", major)
    
    with col2:
        if patterns and 'best_day' in patterns:
            st.metric("Meilleur Jour", patterns['best_day'])
    
    with col3:
        if patterns and 'best_hour' in patterns:
            st.metric("Meilleure Heure", patterns['best_hour'])
    
    with col4:
        st.metric("Prix Actuel", f"${df['close'].iloc[-1]:,.0f}")
    
    # Distribution par jour
    if patterns and 'day_stats' in patterns and not patterns['day_stats'].empty:
        fig = px.bar(
            patterns['day_stats'],
            x='day',
            y='percentage',
            title="Fréquence des bottoms par jour",
            color='avg_strength',
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig, use_container_width=True)

def display_bottoms_charts(df, bottoms, tz_name):
    """Graphiques des bottoms"""
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3]
    )
    
    # Chandelier
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name="BTC"
        ),
        row=1, col=1
    )
    
    # Marquer les bottoms
    if not bottoms.empty:
        colors = {'simple': 'yellow', 'confirmed': 'orange', 'major': 'red'}
        
        for bottom_type in ['major', 'confirmed', 'simple']:
            if 'type' in bottoms.columns:
                type_bottoms = bottoms[bottoms['type'] == bottom_type]
            else:
                type_bottoms = bottoms if bottom_type == 'simple' else pd.DataFrame()
            
            if not type_bottoms.empty:
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
    
    # Volume
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['volume'],
            name="Volume",
            marker_color='lightblue'
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        height=700,
        title=f"Bottoms sur BTC/USDT ({tz_name})",
        xaxis_rangeslider_visible=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_bottoms_patterns(bottoms, patterns, tz_name):
    """Patterns des bottoms"""
    
    if bottoms.empty:
        st.warning("Aucun bottom pour l'analyse des patterns")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Par Jour")
        if patterns and 'day_stats' in patterns:
            st.dataframe(patterns['day_stats'], use_container_width=True)
    
    with col2:
        st.subheader("⏰ Top 5 Heures")
        if not bottoms.empty:
            top_hours = bottoms.groupby('hour').size().sort_values(ascending=False).head(5)
            hour_df = pd.DataFrame({
                'Heure': [f"{h:02d}:00" for h in top_hours.index],
                'Nombre': top_hours.values
            })
            st.dataframe(hour_df, use_container_width=True)

def display_bottoms_backtest(analyzer, patterns, tz_name):
    """Backtest des stratégies bottoms"""
    
    st.subheader("💰 Backtest de Stratégie")
    
    col1, col2 = st.columns(2)
    
    with col1:
        selected_days = st.multiselect(
            "Jours d'achat",
            options=list(DAYS_FR.values()),
            default=[patterns['best_day']] if patterns and 'best_day' in patterns else ["Lundi"]
        )
        day_indices = [k for k, v in DAYS_FR.items() if v in selected_days]
    
    with col2:
        hold_days = st.slider("Période de holding (jours)", 1, 30, 7)
    
    if st.button("🚀 Lancer Backtest"):
        with st.spinner("Calcul..."):
            results = analyzer.backtest_strategy(
                buy_days=day_indices,
                hold_periods=hold_days
            )
            
            if results:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Trades", results['total_trades'])
                with col2:
                    st.metric("Win Rate", f"{results['win_rate']:.1f}%")
                with col3:
                    st.metric("Profit Moy", f"{results['avg_profit']:.2f}%")
                with col4:
                    st.metric("Sharpe", f"{results['sharpe_ratio']:.2f}")

# --- FONCTIONS D'AFFICHAGE POUR TOPS ---

def display_tops_overview_complete(tops, patterns, df, tz_name):
    """Vue d'ensemble complète des tops"""
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Tops", len(tops))
        if 'type' in tops.columns:
            major = len(tops[tops['type'] == 'major'])
            st.metric("Majeurs", major)
    
    with col2:
        if patterns and 'best_day' in patterns:
            st.metric("Jour Fréquent", patterns['best_day'])
    
    with col3:
        if patterns and 'best_hour' in patterns:
            st.metric("Heure Fréquente", patterns['best_hour'])
    
    with col4:
        if 'drop_pct' in tops.columns:
            avg_drop = tops['drop_pct'].mean()
            st.metric("Chute Moyenne", f"{avg_drop:.1f}%")
    
    # Liste des tops récents
    st.subheader(f"📋 Tops Récents ({tz_name})")
    
    if not tops.empty:
        recent_tops = tops.sort_index(ascending=False).head(10)
        display_df = pd.DataFrame({
            'Date': recent_tops.index.strftime('%Y-%m-%d %H:%M'),
            'Prix': recent_tops['price'].apply(lambda x: f"${x:,.0f}"),
            'Type': recent_tops['type'].map({
                'simple': '🟡', 'confirmed': '🟠', 'major': '🔴'
            }) if 'type' in recent_tops.columns else '🟡',
            'Chute': recent_tops['drop_pct'].apply(lambda x: f"{x:.1f}%") if 'drop_pct' in recent_tops.columns else 'N/A'
        })
        st.dataframe(display_df, use_container_width=True)

def display_tops_charts_complete(df, tops, analyzer, tz_name):
    """Graphiques complets des tops"""
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3]
    )
    
    # Chandelier
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name="BTC"
        ),
        row=1, col=1
    )
    
    # Marquer les tops
    if not tops.empty:
        colors = {'simple': 'lightgreen', 'confirmed': 'green', 'major': 'darkgreen'}
        
        for top_type in ['major', 'confirmed', 'simple']:
            if 'type' in tops.columns:
                type_tops = tops[tops['type'] == top_type]
            else:
                type_tops = tops if top_type == 'simple' else pd.DataFrame()
            
            if not type_tops.empty:
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
            marker_color='lightblue'
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        height=700,
        title=f"Tops sur BTC/USDT ({tz_name})",
        xaxis_rangeslider_visible=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_tops_patterns_complete(tops, patterns, tz_name):
    """Patterns complets des tops"""
    
    if tops.empty:
        st.warning("Aucun top détecté")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Par Jour")
        if patterns and 'day_stats' in patterns:
            st.dataframe(patterns['day_stats'], use_container_width=True)
    
    with col2:
        st.subheader("⏰ Top 5 Heures")
        top_hours = tops.groupby('hour').size().sort_values(ascending=False).head(5)
        hour_df = pd.DataFrame({
            'Heure': [f"{h:02d}:00" for h in top_hours.index],
            'Nombre': top_hours.values
        })
        st.dataframe(hour_df, use_container_width=True)

def display_tops_backtest(analyzer, tops, patterns, tz_name):
    """Backtest stratégie short sur les tops"""
    
    st.subheader("💹 Backtest Stratégie Short")
    
    col1, col2 = st.columns(2)
    
    with col1:
        selected_days = st.multiselect(
            "Jours pour shorter",
            options=list(DAYS_FR.values()),
            default=[patterns['best_day']] if patterns and 'best_day' in patterns else ["Lundi"]
        )
        day_indices = [k for k, v in DAYS_FR.items() if v in selected_days]
    
    with col2:
        hold_days = st.slider("Durée du short (jours)", 1, 30, 7)
    
    if st.button("🚀 Lancer Backtest Short"):
        with st.spinner("Calcul..."):
            results = analyzer.backtest_short_strategy(
                sell_days=day_indices,
                hold_periods=hold_days
            )
            
            if results:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Trades", results['total_trades'])
                with col2:
                    st.metric("Win Rate", f"{results['win_rate']:.1f}%")
                with col3:
                    st.metric("Profit Moy", f"{results['avg_profit']:.2f}%")
                with col4:
                    st.metric("Sharpe", f"{results['sharpe_ratio']:.2f}")

def display_tops_detailed_list(tops, tz_name, timeframe):
    """Liste détaillée des tops"""
    
    st.subheader(f"📋 Liste Complète des Tops ({tz_name})")
    
    if tops.empty:
        st.warning("Aucun top détecté")
        return
    
    # Préparer l'affichage
    display_tops = tops.sort_index(ascending=False).copy()
    display_tops['Date'] = display_tops.index.strftime('%Y-%m-%d %H:%M')
    display_tops['Prix'] = display_tops['price'].apply(lambda x: f"${x:,.0f}")
    
    if 'type' in display_tops.columns:
        display_tops['Type'] = display_tops['type'].map({
            'simple': '🟡 Simple',
            'confirmed': '🟠 Confirmé',
            'major': '🔴 Majeur'
        })
    
    if 'drop_pct' in display_tops.columns:
        display_tops['Chute'] = display_tops['drop_pct'].apply(lambda x: f"{x:.1f}%")
    
    if 'rsi' in display_tops.columns:
        display_tops['RSI'] = display_tops['rsi'].apply(lambda x: f"{x:.0f}" if pd.notna(x) else "N/A")
    
    columns = ['Date', 'Prix']
    if 'Type' in display_tops.columns:
        columns.append('Type')
    if 'Chute' in display_tops.columns:
        columns.append('Chute')
    if 'RSI' in display_tops.columns:
        columns.append('RSI')
    
    st.dataframe(display_tops[columns], use_container_width=True, height=500)
    
    # Export
    csv = display_tops[columns].to_csv(index=False)
    st.download_button(
        label="📥 Télécharger CSV",
        data=csv,
        file_name=f"tops_{tz_name}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

def display_tops_temporal_complete(tops, patterns, tz_name):
    """Analyse temporelle complète des tops"""
    
    if tops.empty:
        st.warning("Aucun top pour l'analyse temporelle")
        return
    
    # Distribution horaire
    hourly_counts = tops.groupby('hour').size()
    all_hours = list(range(24))
    hourly_data = [hourly_counts.get(h, 0) for h in all_hours]
    
    fig = go.Figure(go.Bar(
        x=[f"{h:02d}:00" for h in all_hours],
        y=hourly_data,
        marker_color=['green' if d > 0 else 'lightgray' for d in hourly_data],
        text=hourly_data,
        textposition='outside'
    ))
    
    fig.update_layout(
        title=f"Distribution Horaire des Tops ({tz_name})",
        xaxis_title="Heure",
        yaxis_title="Nombre de tops",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_tops_exact_time(tops, selected_tz, tz_name, timeframe):
    """Heure exacte des tops avec données 1 minute"""
    
    st.subheader("🎯 Calcul de l'Heure Exacte des Tops")
    
    if tops.empty:
        st.warning("Aucun top pour l'analyse")
        return
    
    num_tops = st.slider("Nombre de tops à analyser", 1, min(20, len(tops)), 5)
    
    if st.button("🚀 Calculer Heures Exactes des Tops"):
        finder = ExactTopFinder()
        progress_bar = st.progress(0)
        
        tops_to_analyze = tops.head(num_tops)
        results = []
        
        for i, (idx, row) in enumerate(tops_to_analyze.iterrows()):
            progress_bar.progress((i + 1) / len(tops_to_analyze))
            
            # Convertir en UTC pour l'API
            idx_utc = idx.tz_convert('UTC').tz_localize(None) if idx.tz else idx
            
            exact_data = finder.get_exact_top_time(
                approximate_time=idx_utc,
                symbol='BTC/USDT:USDT',
                window_hours=4 if timeframe == '4h' else 1
            )
            
            if exact_data:
                results.append({
                    'Date': idx.strftime('%Y-%m-%d'),
                    'Heure Bougie': idx.strftime('%H:%M'),
                    'Prix': f"${row['price']:,.0f}"
                })
            
            time.sleep(0.5)
        
        if results:
            st.success(f"✅ {len(results)} heures exactes calculées!")
            st.dataframe(pd.DataFrame(results), use_container_width=True)

def display_tops_advanced_scoring(df, tops, tz_name):
    """Scoring avancé pour les tops avec 2 systèmes"""
    
    st.subheader("🎯 Systèmes de Scoring Avancés pour les Tops")
    
    # Choix du système
    scoring_choice = st.radio(
        "Choisir le système de scoring",
        ["📊 Système Multi-Critères", "🤖 Système GPT-5"],
        horizontal=True
    )
    
    if scoring_choice == "📊 Système Multi-Critères":
        create_advanced_tops_scoring_tab(df, tops, tz_name)
    else:
        create_gpt5_tops_scoring_interface(df, tops, tz_name)

# --- FONCTIONS DE COMPARAISON ---

def display_combined_overview(bottoms, tops, df, tz_name):
    """Vue combinée bottoms et tops"""
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Bottoms", len(bottoms))
    with col2:
        st.metric("Total Tops", len(tops))
    with col3:
        ratio = len(tops) / len(bottoms) if len(bottoms) > 0 else 0
        st.metric("Ratio T/B", f"{ratio:.2f}")
    with col4:
        st.metric("Prix Actuel", f"${df['close'].iloc[-1]:,.0f}")

def display_combined_chart(df, bottoms, tops, tz_name):
    """Graphique combiné avec bottoms et tops"""
    
    fig = go.Figure()
    
    # Chandelier
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name="BTC"
    ))
    
    # Bottoms
    if not bottoms.empty:
        fig.add_trace(go.Scatter(
            x=bottoms.index,
            y=bottoms['price'],
            mode='markers',
            marker=dict(size=10, color='red', symbol='triangle-up'),
            name="Bottoms"
        ))
    
    # Tops
    if not tops.empty:
        fig.add_trace(go.Scatter(
            x=tops.index,
            y=tops['price'],
            mode='markers',
            marker=dict(size=10, color='green', symbol='triangle-down'),
            name="Tops"
        ))
    
    fig.update_layout(
        height=700,
        title=f"Vue Combinée Bottoms & Tops ({tz_name})",
        xaxis_rangeslider_visible=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_temporal_comparison(bottoms, tops, tz_name):
    """Comparaison temporelle bottoms vs tops"""
    
    if bottoms.empty or tops.empty:
        st.warning("Données insuffisantes pour la comparaison")
        return
    
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
        y=[-hourly_tops.get(h, 0) for h in all_hours],
        name='Tops',
        marker_color='green'
    ))
    
    fig.update_layout(
        title=f"Distribution Horaire Comparée ({tz_name})",
        xaxis_title="Heure",
        yaxis_title="Bottoms ↑ / Tops ↓",
        barmode='relative',
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_statistics_comparison(bottoms, tops, tz_name):
    """Statistiques comparatives"""
    
    stats_data = {
        'Métrique': ['Total', 'Majeurs', 'Heure Pic', 'Jour Pic'],
        'Bottoms': [
            len(bottoms),
            len(bottoms[bottoms['type'] == 'major']) if 'type' in bottoms.columns else 'N/A',
            f"{int(bottoms.groupby('hour').size().idxmax()):02d}:00" if not bottoms.empty else 'N/A',
            DAYS_FR.get(bottoms.groupby('day_of_week').size().idxmax(), 'N/A') if not bottoms.empty else 'N/A'
        ],
        'Tops': [
            len(tops),
            len(tops[tops['type'] == 'major']) if 'type' in tops.columns else 'N/A',
            f"{int(tops.groupby('hour').size().idxmax()):02d}:00" if not tops.empty else 'N/A',
            DAYS_FR.get(tops.groupby('day_of_week').size().idxmax(), 'N/A') if not tops.empty else 'N/A'
        ]
    }
    
    st.dataframe(pd.DataFrame(stats_data), use_container_width=True)

def display_insights_comparison(bottoms, tops, tz_name):
    """Insights de la comparaison"""
    
    insights = []
    
    if not bottoms.empty and not tops.empty:
        # Décalage horaire
        bottom_hour = int(bottoms.groupby('hour').size().idxmax())
        top_hour = int(tops.groupby('hour').size().idxmax())
        
        if abs(top_hour - bottom_hour) > 6:
            insights.append(f"🔄 Décalage de {abs(top_hour - bottom_hour)}h entre tops et bottoms")
        
        # Ratio
        ratio = len(tops) / len(bottoms)
        if ratio > 1.2:
            insights.append(f"📈 Plus de tops que de bottoms (ratio {ratio:.2f})")
        elif ratio < 0.8:
            insights.append(f"📉 Plus de bottoms que de tops (ratio {ratio:.2f})")
        
        # Volatilité par jour
        top_day = tops.groupby('day_of_week').size().idxmax()
        bottom_day = bottoms.groupby('day_of_week').size().idxmax()
        
        if top_day == bottom_day:
            insights.append(f"⚠️ {DAYS_FR[top_day]} = Jour le plus volatil (tops ET bottoms)")
    
    for insight in insights:
        st.info(insight)

# --- FONCTIONS FAQ ---

def display_faq_bottoms():
    """FAQ pour les bottoms"""
    
    st.subheader("❓ FAQ Bottoms")
    
    with st.expander("Comment sont détectés les bottoms ?"):
        st.markdown("""
        - **Simple** : Plus bas local sur 30 périodes
        - **Confirmé** : + Volume élevé + Rebond > 5%
        - **Majeur** : Plus bas 90 jours + Chute > 20% avant
        """)
    
    with st.expander("Quelle stratégie adopter ?"):
        st.markdown("""
        - **Long terme** : Focus sur bottoms majeurs
        - **Swing** : Bottoms confirmés
        - **DCA** : Utiliser les jours identifiés
        """)

def display_faq_tops():
    """FAQ pour les tops"""
    
    st.subheader("❓ FAQ Tops")
    
    with st.expander("Comment sont détectés les tops ?"):
        st.markdown("""
        - **Simple** : Plus haut local sur 30 périodes
        - **Confirmé** : + RSI > 70 + Chute > 5%
        - **Majeur** : Plus haut 90 jours + Montée > 50% avant
        """)
    
    with st.expander("Quand prendre ses profits ?"):
        st.markdown("""
        - Tops confirmés = Signal de prudence
        - Tops majeurs = Prise de profit recommandée
        - Utiliser l'analyse temporelle pour timing
        """)

# Constantes
DAYS_FR = {0: 'Lundi', 1: 'Mardi', 2: 'Mercredi', 3: 'Jeudi', 4: 'Vendredi', 5: 'Samedi', 6: 'Dimanche'}

if __name__ == "__main__":
    main()