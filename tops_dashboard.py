"""
Dashboard pour l'analyse des tops (sommets)
Interface Streamlit pour visualiser et analyser les tops du Bitcoin
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
from top_analyzer import TopAnalyzer

def create_tops_analysis_tab(df, selected_tz_name, selected_tz):
    """
    Crée l'onglet principal d'analyse des tops
    """
    st.header(f"📈 Analyse des Tops (Sommets) - {selected_tz_name}")
    
    # Sous-onglets
    sub_tab1, sub_tab2, sub_tab3, sub_tab4, sub_tab5 = st.tabs([
        "🎯 Vue d'ensemble",
        "📊 Graphiques", 
        "⏰ Analyse Temporelle",
        "💹 Stratégie Short",
        "🔄 Comparaison Tops/Bottoms"
    ])
    
    # Analyser les tops
    analyzer = TopAnalyzer(df)
    tops = analyzer.detect_tops(method='all')
    
    # Convertir au fuseau horaire sélectionné
    if not tops.empty and selected_tz != "UTC":
        if not tops.index.tz:
            tops.index = tops.index.tz_localize('UTC')
        tops.index = tops.index.tz_convert(selected_tz)
        tops['hour'] = tops.index.hour
        tops['day_of_week'] = tops.index.dayofweek
    
    patterns = analyzer.analyze_patterns() if not tops.empty else {}
    
    with sub_tab1:
        display_tops_overview(tops, patterns, selected_tz_name)
    
    with sub_tab2:
        display_tops_charts(df, tops, analyzer, selected_tz_name)
    
    with sub_tab3:
        display_tops_temporal_analysis(tops, patterns, selected_tz_name)
    
    with sub_tab4:
        display_short_strategy(tops, analyzer, patterns)
    
    with sub_tab5:
        display_tops_bottoms_comparison(df, selected_tz_name, selected_tz)

def display_tops_overview(tops, patterns, selected_tz_name):
    """
    Affiche la vue d'ensemble des tops
    """
    st.subheader("🎯 Vue d'Ensemble des Tops")
    
    if tops.empty:
        st.warning("Aucun top détecté avec les paramètres actuels")
        return
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Tops", len(tops))
        if 'type' in tops.columns:
            major_count = len(tops[tops['type'] == 'major'])
            st.metric("Tops Majeurs", major_count)
    
    with col2:
        if patterns and 'best_day' in patterns:
            st.metric("Jour le Plus Fréquent", patterns['best_day'])
    
    with col3:
        if patterns and 'best_hour' in patterns:
            st.metric("Heure la Plus Fréquente", patterns['best_hour'])
    
    with col4:
        avg_drop = tops['drop_pct'].mean() if 'drop_pct' in tops.columns else 0
        st.metric("Chute Moyenne", f"{avg_drop:.1f}%")
    
    # Types de tops
    st.subheader("📊 Répartition par Type")
    
    if 'type' in tops.columns:
        type_counts = tops['type'].value_counts()
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_pie = px.pie(
                values=type_counts.values,
                names=type_counts.index,
                title="Distribution des Types de Tops",
                color_discrete_map={
                    'simple': '#FFFF00',
                    'confirmed': '#FFA500',
                    'major': '#FF0000'
                }
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Tableau récapitulatif
            summary_df = pd.DataFrame({
                'Type': ['🟡 Simple', '🟠 Confirmé', '🔴 Majeur'],
                'Nombre': [
                    type_counts.get('simple', 0),
                    type_counts.get('confirmed', 0),
                    type_counts.get('major', 0)
                ],
                'Pourcentage': [
                    f"{type_counts.get('simple', 0)/len(tops)*100:.1f}%",
                    f"{type_counts.get('confirmed', 0)/len(tops)*100:.1f}%",
                    f"{type_counts.get('major', 0)/len(tops)*100:.1f}%"
                ]
            })
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
    
    # Liste détaillée des tops récents
    st.subheader(f"📋 Tops Récents ({selected_tz_name})")
    
    # CORRECTION : Trier par index décroissant pour avoir les plus récents en premier
    display_tops = tops.sort_index(ascending=False).head(20).copy()
    display_tops['Date'] = display_tops.index.strftime('%Y-%m-%d %H:%M')
    display_tops['Prix'] = display_tops['price'].apply(lambda x: f"${x:,.0f}")
    
    if 'type' in display_tops.columns:
        type_emojis = {
            'simple': '🟡 Simple',
            'confirmed': '🟠 Confirmé',
            'major': '🔴 Majeur'
        }
        display_tops['Type'] = display_tops['type'].map(type_emojis)
    
    if 'drop_pct' in display_tops.columns:
        display_tops['Chute'] = display_tops['drop_pct'].apply(lambda x: f"📉 {x:.1f}%")
    
    if 'rsi' in display_tops.columns:
        display_tops['RSI'] = display_tops['rsi'].apply(lambda x: f"{x:.0f}" if pd.notna(x) else "N/A")
    
    columns_to_show = ['Date', 'Prix']
    if 'Type' in display_tops.columns:
        columns_to_show.append('Type')
    if 'Chute' in display_tops.columns:
        columns_to_show.append('Chute')
    if 'RSI' in display_tops.columns:
        columns_to_show.append('RSI')
    
    st.dataframe(
        display_tops[columns_to_show],
        use_container_width=True,
        height=400
    )

def display_tops_charts(df, tops, analyzer, selected_tz_name):
    """
    Affiche les graphiques des tops
    """
    st.subheader("📈 Visualisation des Tops")
    
    # Graphique principal
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=("Prix et Tops Identifiés", "Volume")
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
    
    # Marquer les tops
    if not tops.empty:
        colors = {
            'simple': 'yellow',
            'confirmed': 'orange', 
            'major': 'red'
        }
        
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
                            color=colors.get(top_type, 'blue'),
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
        title=f"Tops Identifiés sur BTC/USDT ({selected_tz_name})"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Distribution des prix des tops
    if not tops.empty:
        st.subheader("📊 Distribution des Prix des Tops")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_hist = px.histogram(
                tops,
                x='price',
                nbins=30,
                title="Distribution des Prix",
                labels={'price': 'Prix ($)', 'count': 'Nombre de tops'}
            )
            st.plotly_chart(fig_hist, use_container_width=True)
        
        with col2:
            if 'drop_pct' in tops.columns:
                fig_drop = px.box(
                    tops,
                    y='drop_pct',
                    x='type' if 'type' in tops.columns else None,
                    title="Distribution des Chutes Post-Top",
                    labels={'drop_pct': 'Chute (%)', 'type': 'Type de Top'}
                )
                st.plotly_chart(fig_drop, use_container_width=True)

def display_tops_temporal_analysis(tops, patterns, selected_tz_name):
    """
    Analyse temporelle des tops
    """
    st.subheader(f"⏰ Analyse Temporelle des Tops ({selected_tz_name})")
    
    if tops.empty:
        st.warning("Aucun top pour l'analyse temporelle")
        return
    
    # Distribution par heure
    col1, col2 = st.columns(2)
    
    with col1:
        hourly_counts = tops.groupby('hour').size()
        all_hours = list(range(24))
        hourly_data = [hourly_counts.get(h, 0) for h in all_hours]
        
        fig_hourly = go.Figure(go.Bar(
            x=[f"{h:02d}:00" for h in all_hours],
            y=hourly_data,
            marker_color=['red' if h >= 12 else 'orange' for h in all_hours],
            text=hourly_data,
            textposition='outside'
        ))
        
        fig_hourly.update_layout(
            title=f"Tops par Heure ({selected_tz_name})",
            xaxis_title="Heure",
            yaxis_title="Nombre de tops",
            height=400
        )
        
        st.plotly_chart(fig_hourly, use_container_width=True)
    
    with col2:
        # Vue horloge
        theta = [h * 15 for h in all_hours]
        
        fig_clock = go.Figure(go.Scatterpolar(
            r=hourly_data,
            theta=theta,
            fill='toself',
            fillcolor='rgba(255, 0, 0, 0.3)',
            line=dict(color='red', width=2),
            marker=dict(size=8, color='darkred')
        ))
        
        fig_clock.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, max(hourly_data) * 1.1] if hourly_data else [0, 1]
                ),
                angularaxis=dict(
                    tickmode='array',
                    tickvals=theta,
                    ticktext=[f"{h:02d}h" for h in all_hours],
                    direction='clockwise',
                    rotation=90
                )
            ),
            title=f"Vue Horloge des Tops ({selected_tz_name})",
            height=400
        )
        
        st.plotly_chart(fig_clock, use_container_width=True)
    
    # Heatmap jour/heure
    st.subheader("🗓️ Heatmap Jour × Heure")
    
    DAYS_FR = {0: 'Lundi', 1: 'Mardi', 2: 'Mercredi', 3: 'Jeudi', 4: 'Vendredi', 5: 'Samedi', 6: 'Dimanche'}
    
    pivot_table = tops.pivot_table(
        index='day_of_week',
        columns='hour',
        values='price',
        aggfunc='count',
        fill_value=0
    )
    
    if not pivot_table.empty:
        pivot_table.index = [DAYS_FR[i] for i in pivot_table.index]
        
        fig_heatmap = go.Figure(data=go.Heatmap(
            z=pivot_table.values,
            x=[f"{h:02d}:00" for h in pivot_table.columns],
            y=pivot_table.index,
            colorscale='Reds',
            text=pivot_table.values,
            texttemplate='%{text}',
            textfont={"size": 10}
        ))
        
        fig_heatmap.update_layout(
            title=f"Heatmap des Tops par Jour et Heure ({selected_tz_name})",
            xaxis_title="Heure",
            yaxis_title="Jour",
            height=400
        )
        
        st.plotly_chart(fig_heatmap, use_container_width=True)
    
    # Top 5 heures dangereuses pour shorter
    st.subheader("🎯 Meilleurs Moments pour Shorter")
    
    if patterns and 'hour_stats' in patterns:
        hour_stats = patterns['hour_stats'].nlargest(5, 'count')
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📈 Top 5 Heures avec le Plus de Tops")
            for idx, row in hour_stats.iterrows():
                st.markdown(f"**{int(row['hour']):02d}:00** - {int(row['count'])} tops ({row['percentage']:.1f}%)")
        
        with col2:
            st.info("""
            💡 **Stratégie de Short**
            
            Les heures avec le plus de tops sont potentiellement
            les meilleurs moments pour :
            - Prendre des profits (si long)
            - Initier des positions short
            - Réduire l'exposition
            """)

def display_short_strategy(tops, analyzer, patterns):
    """
    Backtest de stratégie de short basée sur les tops
    """
    st.subheader("💹 Stratégie de Short sur les Tops")
    
    if tops.empty:
        st.warning("Aucun top pour le backtest")
        return
    
    # Paramètres
    col1, col2 = st.columns(2)
    
    with col1:
        DAYS_FR = {0: 'Lundi', 1: 'Mardi', 2: 'Mercredi', 3: 'Jeudi', 4: 'Vendredi', 5: 'Samedi', 6: 'Dimanche'}
        
        selected_days = st.multiselect(
            "Jours pour shorter",
            options=list(DAYS_FR.values()),
            default=[patterns['best_day']] if patterns and 'best_day' in patterns else ["Lundi"]
        )
        
        # Convertir en indices
        day_indices = [k for k, v in DAYS_FR.items() if v in selected_days]
    
    with col2:
        hold_days = st.slider(
            "Durée du short (jours)",
            min_value=1,
            max_value=30,
            value=7
        )
    
    if st.button("🚀 Lancer Backtest Short", type="primary"):
        with st.spinner("Backtest en cours..."):
            results = analyzer.backtest_short_strategy(
                sell_days=day_indices,
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
                st.success(f"✅ Stratégie de short prometteuse le {', '.join(selected_days)}")
            else:
                st.warning(f"⚠️ Stratégie de short peu rentable pour {', '.join(selected_days)}")

def display_tops_bottoms_comparison(df, selected_tz_name, selected_tz):
    """
    Compare les tops et les bottoms
    """
    st.subheader("🔄 Comparaison Tops vs Bottoms")
    
    from bottom_analyzer import BottomAnalyzer
    
    # Analyser les deux
    top_analyzer = TopAnalyzer(df)
    bottom_analyzer = BottomAnalyzer(df)
    
    tops = top_analyzer.detect_tops(method='all')
    bottoms = bottom_analyzer.detect_bottoms(method='all')
    
    # Convertir au fuseau
    if selected_tz != "UTC":
        if not tops.empty:
            if not tops.index.tz:
                tops.index = tops.index.tz_localize('UTC')
            tops.index = tops.index.tz_convert(selected_tz)
            tops['hour'] = tops.index.hour
            tops['day_of_week'] = tops.index.dayofweek
        
        if not bottoms.empty:
            if not bottoms.index.tz:
                bottoms.index = bottoms.index.tz_localize('UTC')
            bottoms.index = bottoms.index.tz_convert(selected_tz)
            bottoms['hour'] = bottoms.index.hour
            bottoms['day_of_week'] = bottoms.index.dayofweek
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📉 Bottoms")
        st.metric("Total", len(bottoms))
        if not bottoms.empty:
            st.metric("Heure la plus fréquente", f"{int(bottoms.groupby('hour').size().idxmax()):02d}:00")
            DAYS_FR = {0: 'Lundi', 1: 'Mardi', 2: 'Mercredi', 3: 'Jeudi', 4: 'Vendredi', 5: 'Samedi', 6: 'Dimanche'}
            st.metric("Jour le plus fréquent", DAYS_FR[bottoms.groupby('day_of_week').size().idxmax()])
    
    with col2:
        st.markdown("### 📈 Tops")
        st.metric("Total", len(tops))
        if not tops.empty:
            st.metric("Heure la plus fréquente", f"{int(tops.groupby('hour').size().idxmax()):02d}:00")
            DAYS_FR = {0: 'Lundi', 1: 'Mardi', 2: 'Mercredi', 3: 'Jeudi', 4: 'Vendredi', 5: 'Samedi', 6: 'Dimanche'}
            st.metric("Jour le plus fréquent", DAYS_FR[tops.groupby('day_of_week').size().idxmax()])
    
    # Graphique combiné
    st.subheader("📊 Distribution Horaire Comparée")
    
    if not tops.empty and not bottoms.empty:
        hourly_tops = tops.groupby('hour').size()
        hourly_bottoms = bottoms.groupby('hour').size()
        
        all_hours = list(range(24))
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=[f"{h:02d}:00" for h in all_hours],
            y=[hourly_bottoms.get(h, 0) for h in all_hours],
            name='Bottoms',
            marker_color='green'
        ))
        
        fig.add_trace(go.Bar(
            x=[f"{h:02d}:00" for h in all_hours],
            y=[-hourly_tops.get(h, 0) for h in all_hours],
            name='Tops',
            marker_color='red'
        ))
        
        fig.update_layout(
            title=f"Distribution Horaire Tops vs Bottoms ({selected_tz_name})",
            xaxis_title="Heure",
            yaxis_title="Nombre (Bottoms ↑ / Tops ↓)",
            barmode='relative',
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Insights
    st.subheader("💡 Insights Clés")
    
    insights = []
    
    if not tops.empty and not bottoms.empty:
        top_hour = int(tops.groupby('hour').size().idxmax())
        bottom_hour = int(bottoms.groupby('hour').size().idxmax())
        
        if abs(top_hour - bottom_hour) > 6:
            insights.append(f"🔄 Les tops et bottoms sont décalés de {abs(top_hour - bottom_hour)}h")
        
        if tops.groupby('day_of_week').size().idxmax() == bottoms.groupby('day_of_week').size().idxmax():
            insights.append("⚠️ Même jour pour tops et bottoms = Forte volatilité")
        
        insights.append(f"📊 Ratio Tops/Bottoms: {len(tops)/len(bottoms):.2f}")
    
    for insight in insights:
        st.info(insight)