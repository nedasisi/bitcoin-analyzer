"""
Dashboard interactif Bitcoin Bottom Analyzer
Analyse les patterns des bottoms du BTC depuis 2019
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
from batch_analyzer import BatchExactTimeAnalyzer
from temporal_analysis import create_temporal_analysis_tab
from advanced_dashboard import create_advanced_analysis_tab
from enhanced_exact_time_tab import display_exact_time_tab_with_full_analysis
from tops_dashboard import create_tops_analysis_tab

# Configuration de la page
st.set_page_config(**PAGE_CONFIG)

# CSS personnalisé
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    .plot-container {
        border: 1px solid #e0e0e0;
        border-radius: 5px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Titre principal
st.title("🔍 Bitcoin Bottom Analyzer - BTCUSDT.P")
st.markdown("*Analyse des patterns de bottoms depuis juillet 2019*")

# Sidebar pour les paramètres
with st.sidebar:
    st.header("⚙️ Paramètres")
    
    # Sélecteur de fuseau horaire
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
        index=2,  # Index 2 = Paris (0=UTC, 1=NY, 2=Paris, 3=Bangkok)
        help="Toutes les heures seront converties dans ce fuseau"
    )
    selected_tz = timezone_options[selected_tz_name]
    
    # Afficher l'heure actuelle dans le fuseau sélectionné
    tz_obj = pytz.timezone(selected_tz)
    current_time = datetime.now(tz_obj)
    st.caption(f"🕒 Heure actuelle : {current_time.strftime('%H:%M')} ({selected_tz_name})")
    
    # Info sur les sessions de trading
    if selected_tz != "UTC":
        with st.expander("📈 Sessions de Trading", expanded=False):
            if selected_tz == "America/New_York":
                st.markdown("""
                **New York (EST/EDT):**
                - Asie : 19h-03h
                - Europe : 03h-11h  
                - US : 11h-19h
                """)
            elif selected_tz == "Europe/Paris":
                st.markdown("""
                **Paris (CET/CEST):**
                - Asie : 01h-09h
                - Europe : 09h-17h
                - US : 17h-01h
                """)
            elif selected_tz == "Asia/Bangkok":
                st.markdown("""
                **Bangkok (ICT):**
                - Asie : 07h-15h
                - Europe : 15h-23h
                - US : 23h-07h
                """)
    
    st.markdown("---")
    
    # Sélecteur de Timeframe
    st.subheader("⏱️ Précision Temporelle")
    selected_timeframe = st.selectbox(
        "Choisir le timeframe",
        list(TIMEFRAMES.keys()),
        index=list(TIMEFRAMES.keys()).index(DEFAULT_TIMEFRAME),
        help="1h = plus précis, 4h = moins de bruit"
    )
    
    # Afficher l'info sur la précision
    precision_info = {
        "5m": "🎯 Très précis (±5 min) - Beaucoup de données",
        "15m": "🎯 Précis (±15 min) - Données importantes",
        "30m": "✅ Bonne précision (±30 min)",
        "1h": "✅ Recommandé (±1 heure)",
        "2h": "🔶 Standard (±2 heures)",
        "4h": "🔶 Moins précis (±4 heures)",
        "1d": "⚠️ Peu précis (±1 jour)"
    }
    st.caption(precision_info.get(selected_timeframe, ""))
    
    # Ajuster automatiquement les paramètres selon le timeframe
    multiplier = TIMEFRAME_MULTIPLIERS.get(selected_timeframe, 1)
    adjusted_lookback = int(BOTTOM_PARAMS['lookback_periods'] * multiplier)
    
    st.markdown("---")
    
    # Type de bottom à analyser
    bottom_type = st.selectbox(
        "Type de bottoms",
        ["Tous", "Simples", "Confirmés", "Majeurs"],
        help="Majeurs = bottoms les plus significatifs"
    )
    
    # Explication des types de bottoms
    with st.expander("📚 Comprendre les Types de Bottoms", expanded=False):
        st.markdown("""
        ### 🟡 **Bottom Simple**
        - **Définition** : Point le plus bas sur 30 périodes (5 jours)
        - **Détection** : Minimum local basique
        - **Fiabilité** : ⭐⭐☆☆☆
        - **Usage** : Identifier tous les creux potentiels
        
        ### 🟠 **Bottom Confirmé**
        - **Définition** : Bottom avec rebond validé
        - **Critères** :
            - Rebond minimum de 5% après le creux
            - Volume > 1.5x la moyenne (capitulation)
            - RSI < 30 (survente technique)
        - **Fiabilité** : ⭐⭐⭐⭐☆
        - **Usage** : Trading court/moyen terme
        
        ### 🔴 **Bottom Majeur**
        - **Définition** : Point bas significatif de marché
        - **Critères** :
            - Plus bas sur 90 jours (3 mois)
            - Chute préalable > 20%
            - Rebond confirmé > 15%
            - Volume de capitulation extrême
        - **Fiabilité** : ⭐⭐⭐⭐⭐
        - **Usage** : Investissement long terme
        
        ### 💡 **Recommandation**
        - **Débutants** : Focus sur "Majeurs"
        - **Traders actifs** : "Confirmés"
        - **Analyse complète** : "Tous"
        """)
    
    st.markdown("---")
    
    # Période d'analyse
    date_range = st.date_input(
        "Période d'analyse",
        value=(datetime(2019, 7, 1), datetime.now()),
        min_value=datetime(2019, 7, 1),
        max_value=datetime.now()
    )
    
    # Paramètres avancés
    with st.expander("Paramètres avancés"):
        lookback = st.slider(
            "Périodes de lookback",
            min_value=10,
            max_value=500,
            value=adjusted_lookback,
            help=f"Ajusté pour {selected_timeframe}: {adjusted_lookback} périodes"
        )
        
        min_bounce = st.slider(
            "Rebond minimum (%)",
            min_value=1,
            max_value=20,
            value=BOTTOM_PARAMS['min_bounce_percent'],
            help="Rebond minimum pour confirmer un bottom"
        )
        
        volume_threshold = st.slider(
            "Seuil de volume (x)",
            min_value=1.0,
            max_value=5.0,
            value=BOTTOM_PARAMS['volume_threshold'],
            step=0.5,
            help="Multiple du volume moyen"
        )
    
    # Bouton refresh
    if st.button("🔄 Actualiser les données"):
        st.cache_data.clear()
        st.rerun()

# Fonction pour convertir les heures selon le fuseau
def convert_to_timezone(df_bottoms, timezone_str):
    """
    Convertit les heures des bottoms dans le fuseau horaire sélectionné
    """
    if df_bottoms.empty or timezone_str == "UTC":
        return df_bottoms
    
    df_converted = df_bottoms.copy()
    
    # Convertir l'index (timestamps) en timezone aware UTC puis vers le timezone cible
    if not df_converted.index.tz:
        df_converted.index = df_converted.index.tz_localize('UTC')
    
    df_converted.index = df_converted.index.tz_convert(timezone_str)
    
    # Convertir aussi l'heure exacte si elle existe
    if 'exact_time' in df_converted.columns:
        df_converted['exact_time'] = pd.to_datetime(df_converted['exact_time'])
        if not df_converted['exact_time'].dt.tz:
            df_converted['exact_time'] = df_converted['exact_time'].dt.tz_localize('UTC')
        df_converted['exact_time'] = df_converted['exact_time'].dt.tz_convert(timezone_str)
    
    # Recalculer les heures et jours dans le nouveau fuseau
    df_converted['hour'] = df_converted.index.hour
    df_converted['day_of_week'] = df_converted.index.dayofweek
    
    return df_converted

# Fonction de chargement des données avec cache
@st.cache_data(ttl=3600)
def load_data(timeframe="1h"):
    """Charge les données avec cache de 1h"""
    with st.spinner(f"Chargement des données en {timeframe}..."):
        collector = DataCollector()
        # Mettre à jour le timeframe global
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
    # Mettre à jour les paramètres
    BOTTOM_PARAMS['lookback_periods'] = lookback
    BOTTOM_PARAMS['min_bounce_percent'] = min_bounce
    BOTTOM_PARAMS['volume_threshold'] = volume_threshold
    
    analyzer = BottomAnalyzer(df)
    
    # Détecter les bottoms
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

# Chargement des données
df = load_data(selected_timeframe)

if df is not None:
    # Filtrer par date
    if len(date_range) == 2:
        mask = (df.index >= pd.Timestamp(date_range[0])) & (df.index <= pd.Timestamp(date_range[1]))
        df_filtered = df.loc[mask]
    else:
        df_filtered = df
    
    # Analyser les bottoms
    bottoms, patterns, analyzer = analyze_bottoms(
        df_filtered, 
        bottom_type,
        lookback,
        min_bounce,
        volume_threshold
    )
    
    # Ajouter les heures exactes estimées aux bottoms
    if not bottoms.empty:
        bottoms = add_exact_times_to_bottoms(bottoms, df_filtered, selected_timeframe)
    
    # Convertir les bottoms dans le fuseau horaire sélectionné
    bottoms_tz = convert_to_timezone(bottoms, selected_tz)
    
    # Réanalyser les patterns avec les nouvelles heures
    if not bottoms_tz.empty:
        analyzer.bottoms = bottoms_tz
        patterns = analyzer.analyze_patterns()
    
    # Onglets principaux
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
        "📊 Vue d'ensemble", 
        "📈 Graphiques", 
        "🎯 Patterns",
        "💰 Backtest",
        "📉 Bottoms Détails",
        "❓ FAQ & Tips",
        "🎯 Heure Exacte (1min)",
        "⏰ Analyse Temporelle",
        "🎯 Scoring Avancé",
        "📈 TOPS (Sommets)"
    ])
    
    with tab1:
        st.header("Vue d'ensemble")
        
        # Afficher le timeframe actuel et la précision
        st.info(f"🎯 **Précision actuelle**: ±{TIMEFRAMES[selected_timeframe]} | **Timeframe**: {selected_timeframe} | **Périodes analysées**: {len(df_filtered) if df_filtered is not None else 0}")
        
        # Légende des types de bottoms
        with st.expander("🎯 Légende des Bottoms", expanded=True):
            col_leg1, col_leg2, col_leg3 = st.columns(3)
            
            with col_leg1:
                st.markdown("""
                <div style="background-color: #fff3cd; padding: 10px; border-radius: 5px; border-left: 4px solid #ffc107;">
                    <strong>🟡 Simple</strong><br>
                    <small>Minimum local<br>Fiabilité: ⭐⭐☆</small>
                </div>
                """, unsafe_allow_html=True)
            
            with col_leg2:
                st.markdown("""
                <div style="background-color: #ffe5d5; padding: 10px; border-radius: 5px; border-left: 4px solid #ff6b35;">
                    <strong>🟠 Confirmé</strong><br>
                    <small>Rebond + Volume<br>Fiabilité: ⭐⭐⭐⭐</small>
                </div>
                """, unsafe_allow_html=True)
            
            with col_leg3:
                st.markdown("""
                <div style="background-color: #ffd5d5; padding: 10px; border-radius: 5px; border-left: 4px solid #dc3545;">
                    <strong>🔴 Majeur</strong><br>
                    <small>Bottom de marché<br>Fiabilité: ⭐⭐⭐⭐⭐</small>
                </div>
                """, unsafe_allow_html=True)
        
        # Métriques principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Bottoms",
                f"{len(bottoms)}",
                f"Sur {len(df_filtered)} bougies"
            )
        
        with col2:
            if patterns and 'best_day' in patterns:
                st.metric(
                    "Meilleur Jour",
                    patterns['best_day'],
                    f"Le plus fréquent"
                )
        
        with col3:
            if patterns and 'best_hour' in patterns:
                st.metric(
                    "Meilleure Heure",
                    patterns['best_hour'],
                    selected_tz_name if selected_tz != "UTC" else "UTC"
                )
        
        with col4:
            st.metric(
                "Prix Actuel",
                f"${df_filtered['close'].iloc[-1]:,.0f}",
                f"{((df_filtered['close'].iloc[-1] - df_filtered['close'].iloc[-2]) / df_filtered['close'].iloc[-2] * 100):.2f}%"
            )
        
        # Distribution par jour
        st.subheader("📅 Distribution des Bottoms par Jour de la Semaine")
        
        if patterns and 'day_stats' in patterns and not patterns['day_stats'].empty:
            fig_days = px.bar(
                patterns['day_stats'],
                x='day',
                y='percentage',
                color='avg_strength',
                color_continuous_scale='RdYlGn',
                labels={'percentage': 'Pourcentage (%)', 'day': 'Jour', 'avg_strength': 'Force'},
                title="Fréquence des bottoms par jour"
            )
            fig_days.update_layout(height=400)
            st.plotly_chart(fig_days, use_container_width=True)
            
            # Tableau détaillé
            st.dataframe(
                patterns['day_stats'].style.format({
                    'percentage': '{:.1f}%',
                    'avg_strength': '{:.2f}'
                }).background_gradient(subset=['percentage'], cmap='RdYlGn'),
                use_container_width=True
            )
        
        # Sessions de trading
        st.subheader("🌍 Distribution par Session de Trading")
        
        if patterns and 'session_stats' in patterns and not patterns['session_stats'].empty:
            col1, col2 = st.columns(2)
            
            with col1:
                fig_sessions = px.pie(
                    patterns['session_stats'],
                    values='count',
                    names='session',
                    title="Répartition par session"
                )
                st.plotly_chart(fig_sessions, use_container_width=True)
            
            with col2:
                st.dataframe(
                    patterns['session_stats'].style.format({
                        'percentage': '{:.1f}%'
                    }),
                    use_container_width=True
                )
    
    with tab2:
        st.header("Graphiques Détaillés")
        
        # Graphique principal avec bottoms
        st.subheader("📉 Prix et Bottoms Identifiés")
        
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3],
            subplot_titles=("Prix BTC/USDT", "Volume & RSI")
        )
        
        # Chandelier
        fig.add_trace(
            go.Candlestick(
                x=df_filtered.index,
                open=df_filtered['open'],
                high=df_filtered['high'],
                low=df_filtered['low'],
                close=df_filtered['close'],
                name="BTC"
            ),
            row=1, col=1
        )
        
        # Marquer les bottoms
        if not bottoms.empty:
            colors = {
                'simple': 'yellow',
                'confirmed': 'orange',
                'major': 'red'
            }
            
            for bottom_type_iter in bottoms['type'].unique() if 'type' in bottoms.columns else ['simple']:
                type_bottoms = bottoms[bottoms['type'] == bottom_type_iter] if 'type' in bottoms.columns else bottoms
                
                fig.add_trace(
                    go.Scatter(
                        x=type_bottoms.index,
                        y=type_bottoms['price'],
                        mode='markers',
                        marker=dict(
                            size=10,
                            color=colors.get(bottom_type_iter, 'blue'),
                            symbol='triangle-up'
                        ),
                        name=f"Bottom {bottom_type_iter}"
                    ),
                    row=1, col=1
                )
        
        # Volume
        fig.add_trace(
            go.Bar(
                x=df_filtered.index,
                y=df_filtered['volume'],
                name="Volume",
                marker_color='lightblue'
            ),
            row=2, col=1
        )
        
        # RSI si disponible
        if 'rsi' in df_filtered.columns:
            fig.add_trace(
                go.Scatter(
                    x=df_filtered.index,
                    y=df_filtered['rsi'],
                    name="RSI",
                    line=dict(color='purple'),
                    yaxis="y3"
                ),
                row=2, col=1
            )
            
            # Ligne RSI 30
            fig.add_hline(
                y=30, 
                line_dash="dash", 
                line_color="red",
                row=2, col=1
            )
        
        fig.update_layout(
            height=800,
            xaxis_rangeslider_visible=False,
            yaxis3=dict(
                title="RSI",
                overlaying="y2",
                side="right"
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Heatmap des bottoms
        st.subheader("🗓️ Heatmap Jour/Heure")
        
        if not bottoms.empty:
            # Créer une matrice jour/heure
            heatmap_data = bottoms.groupby(['day_of_week', 'hour']).size().unstack(fill_value=0)
            
            # Renommer les jours
            heatmap_data.index = [DAYS_FR[i] for i in heatmap_data.index]
            
            fig_heatmap = px.imshow(
                heatmap_data,
                labels=dict(x="Heure (UTC)", y="Jour", color="Nombre"),
                color_continuous_scale="YlOrRd",
                title="Distribution des bottoms par jour et heure"
            )
            fig_heatmap.update_layout(height=400)
            st.plotly_chart(fig_heatmap, use_container_width=True)
    
    with tab3:
        st.header("Analyse des Patterns")
        
        # Statistiques avancées
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Statistiques par Jour")
            
            if not bottoms.empty:
                day_analysis = []
                for day in range(7):
                    day_bottoms = bottoms[bottoms['day_of_week'] == day]
                    if len(day_bottoms) > 0:
                        day_analysis.append({
                            'Jour': DAYS_FR[day],
                            'Nombre': len(day_bottoms),
                            'Pourcentage': f"{len(day_bottoms)/len(bottoms)*100:.1f}%",
                            'Force Moy': f"{day_bottoms['strength'].mean():.2f}" if 'strength' in day_bottoms.columns else "N/A"
                        })
                
                st.dataframe(pd.DataFrame(day_analysis), use_container_width=True)
        
        with col2:
            st.subheader("⏰ Top 5 Heures")
            
            if not bottoms.empty:
                top_hours = bottoms.groupby('hour').size().sort_values(ascending=False).head(5)
                hour_df = pd.DataFrame({
                    'Heure': [f"{h:02d}:00" for h in top_hours.index],
                    'Nombre': top_hours.values,
                    'Pourcentage': [f"{v/len(bottoms)*100:.1f}%" for v in top_hours.values]
                })
                st.dataframe(hour_df, use_container_width=True)
        
        # Analyse temporelle
        st.subheader("📈 Évolution dans le Temps")
        
        if not bottoms.empty:
            # Bottoms par mois
            bottoms_monthly = bottoms.groupby(pd.Grouper(freq='M')).size()
            
            fig_timeline = go.Figure()
            fig_timeline.add_trace(go.Scatter(
                x=bottoms_monthly.index,
                y=bottoms_monthly.values,
                mode='lines+markers',
                name='Bottoms par mois',
                line=dict(color='blue', width=2)
            ))
            fig_timeline.update_layout(
                title="Nombre de bottoms par mois",
                xaxis_title="Date",
                yaxis_title="Nombre de bottoms",
                height=400
            )
            st.plotly_chart(fig_timeline, use_container_width=True)
    
    with tab4:
        st.header("Backtest de Stratégies")
        
        # Explication du backtest
        col_info1, col_info2 = st.columns(2)
        
        with col_info1:
            st.info("""
            💡 **Comment ça marche ?**
            
            Ce backtest simule une stratégie d'achat régulier:
            - Acheter le(s) jour(s) sélectionné(s)
            - Tenir la position X jours
            - Vendre automatiquement
            - Mesurer la performance
            """)
        
        with col_info2:
            st.success("""
            🎯 **Interprétation des résultats**
            
            - **Taux > 55%** = Stratégie prometteuse
            - **Profit moyen > 2%** = Bon pour le swing
            - **Sharpe > 1** = Bon ratio risque/récompense
            - **Test sur 100+ trades** = Plus fiable
            """)
        
        # Sélection des jours
        selected_days = st.multiselect(
            "Jours d'achat",
            options=list(DAYS_FR.values()),
            default=[patterns['best_day']] if patterns and 'best_day' in patterns else ["Lundi"]
        )
        
        # Convertir en indices
        day_indices = [k for k, v in DAYS_FR.items() if v in selected_days]
        
        # Période de holding
        hold_days = st.slider(
            "Période de holding (jours)",
            min_value=1,
            max_value=30,
            value=7
        )
        
        if st.button("🚀 Lancer le Backtest"):
            with st.spinner("Calcul en cours..."):
                results = analyzer.backtest_strategy(
                    buy_days=day_indices,
                    hold_periods=hold_days
                )
                
                if results:
                    # Afficher les résultats
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Trades Total", results['total_trades'])
                    with col2:
                        st.metric("Taux de Réussite", f"{results['win_rate']:.1f}%")
                    with col3:
                        st.metric("Profit Moyen", f"{results['avg_profit']:.2f}%")
                    with col4:
                        st.metric("Sharpe Ratio", f"{results['sharpe_ratio']:.2f}")
                    
                    # Détails
                    st.subheader("📊 Détails de Performance")
                    
                    perf_data = {
                        'Métrique': [
                            'Trades Gagnants',
                            'Profit Médian',
                            'Meilleur Trade',
                            'Pire Trade'
                        ],
                        'Valeur': [
                            f"{results['winning_trades']}",
                            f"{results['median_profit']:.2f}%",
                            f"{results['max_profit']:.2f}%",
                            f"{results['max_loss']:.2f}%"
                        ]
                    }
                    
                    st.dataframe(pd.DataFrame(perf_data), use_container_width=True)
                    
                    # Recommandation
                    if results['win_rate'] > 55 and results['avg_profit'] > 0:
                        st.success(f"✅ Stratégie prometteuse ! Acheter le {', '.join(selected_days)} semble profitable.")
                    elif results['win_rate'] > 50:
                        st.warning(f"⚠️ Stratégie moyenne. Résultats mitigés pour {', '.join(selected_days)}.")
                    else:
                        st.error(f"❌ Stratégie non recommandée pour {', '.join(selected_days)}.")
    
    with tab5:
        # Utiliser la nouvelle fonction d'affichage avec heure exacte
        display_bottoms_with_exact_time(bottoms_tz, selected_tz_name, selected_timeframe, TIMEFRAMES, DAYS_FR)
    
    with tab6:
        st.header("❓ FAQ & Tips d'utilisation")
        
        # FAQ
        st.subheader("📖 Questions Fréquentes")
        
        with st.expander("🕒 Comment la précision temporelle affecte les résultats ?"):
            st.markdown(f"""
            **Timeframe actuel : {selected_timeframe}**
            
            - **5m/15m** : Détecte l'heure exacte mais beaucoup de "faux" bottoms
            - **30m/1h** : Bon équilibre précision/fiabilité (recommandé)
            - **2h/4h** : Moins précis mais bottoms plus significatifs
            - **1d** : Seulement les bottoms majeurs
            
            💡 **Votre exemple** : Bottom du 01/09 à 07:19
            - En 4h : Affiché 04:00 (début de la bougie)
            - En 1h : Affiché 07:00 (plus précis)
            - En 15m : Affiché 07:15 (très précis)
            """)
        
        with st.expander("🤔 Pourquoi analyser les bottoms par jour de la semaine ?"):
            st.markdown("""
            Les marchés crypto présentent des patterns récurrents liés à:
            - **Weekend** : Moins de volume institutionnel
            - **Lundi** : Retour des traders, réactions aux news du weekend
            - **Vendredi** : Prises de profit avant le weekend
            - **Funding rates** : Paiements toutes les 8h (00h, 08h, 16h UTC)
            """)
        
        with st.expander("📊 Comment interpréter les résultats ?"):
            st.markdown("""
            1. **Jour avec le plus de bottoms** = Potentiel point d'entrée récurrent
            2. **Heatmap jour/heure** = Moments précis de faiblesse
            3. **Sessions de trading** = Impact des différents marchés
            4. **Force moyenne** = Qualité des bottoms ce jour-là
            """)
        
        with st.expander("🎯 Quelle stratégie adopter ?"):
            st.markdown("""
            **Pour les investisseurs long terme:**
            - Focus sur les **Bottoms Majeurs** uniquement
            - Attendre confirmation sur plusieurs jours
            - DCA (Dollar Cost Averaging) le jour identifié
            
            **Pour les traders court terme:**
            - Utiliser les **Bottoms Confirmés**
            - Placer des ordres limites aux niveaux clés
            - Stop loss serré sous le bottom
            """)
        
        with st.expander("⚠️ Limites de cette analyse"):
            st.markdown("""
            - **Passé ≠ Futur** : Les patterns peuvent changer
            - **Facteurs externes** : News, régulations, macro non pris en compte
            - **Liquidité** : Les bottoms dépendent aussi du volume
            - **Timeframe** : Analyse en 4h, peut différer en 1h ou daily
            """)
        
        # Tips pratiques
        st.subheader("💡 Tips Pratiques")
        
        col_tip1, col_tip2 = st.columns(2)
        
        with col_tip1:
            st.success("""
            **✅ Bonnes Pratiques**
            - Combiner avec d'autres indicateurs
            - Tester sur papier avant de trader
            - Diversifier les points d'entrée
            - Garder du capital pour moyenner
            - Vérifier le volume de confirmation
            """)
        
        with col_tip2:
            st.error("""
            **❌ À Éviter**
            - All-in sur un seul signal
            - Ignorer la tendance générale
            - Trading émotionnel
            - Oublier les stop loss
            - Sur-optimiser sur l'historique
            """)
        
        # Glossaire
        st.subheader("📑 Glossaire")
        
        glossary = {
            "RSI": "Relative Strength Index - Indicateur de survente/surachat (0-100)",
            "DCA": "Dollar Cost Averaging - Achat régulier pour lisser le prix",
            "Funding Rate": "Taux de financement des futures perpetual",
            "Volume Spike": "Augmentation soudaine du volume (souvent capitulation)",
            "Bounce": "Rebond après un bottom",
            "Capitulation": "Vente massive par panique créant un bottom",
            "Support": "Niveau de prix où les acheteurs interviennent",
            "Sharpe Ratio": "Mesure du rendement ajusté au risque"
        }
        
        for term, definition in glossary.items():
            st.markdown(f"**{term}** : {definition}")
    
    with tab7:
        # Utiliser la version améliorée avec les 3 modes
        display_exact_time_tab_with_full_analysis(bottoms_tz, selected_tz, selected_tz_name, selected_timeframe)
    
    with tab8:
        # Nouvel onglet d'analyse temporelle avancée
        create_temporal_analysis_tab(bottoms_tz, selected_tz_name, patterns, DAYS_FR)
    
    with tab9:
        # Nouvel onglet de scoring avancé basé sur GPT-5
        create_advanced_analysis_tab(df_filtered, selected_tz_name)
    
    with tab10:
        # Nouvel onglet pour l'analyse des TOPS
        create_tops_analysis_tab(df_filtered, selected_tz_name, selected_tz)

else:
    st.error("❌ Impossible de charger les données. Vérifiez votre connexion.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <small>
    Bitcoin Bottom Analyzer v1.1 | Données: BTCUSDT.P depuis 2019<br>
    Fuseau horaire actuel: {}<br>
    ⚠️ Ceci n'est pas un conseil financier. Tradez à vos risques et périls.
    </small>
</div>
""".format(selected_tz_name), unsafe_allow_html=True)