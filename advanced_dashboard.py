"""
Dashboard pour l'analyse avancée avec système de scoring
Interface Streamlit pour la stratégie "excès 4H"
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from advanced_analyzer import AdvancedBottomAnalyzer

def create_advanced_analysis_tab(df, selected_tz_name):
    """
    Crée l'onglet d'analyse avancée avec système de scoring
    """
    st.header("🎯 Analyse Avancée - Système de Scoring (Méthode Excès 4H)")
    
    # Explication du système
    with st.expander("📖 Comprendre le Système de Scoring", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            **📊 Indicateurs (Score 0-10)**
            - Band Z < -0.10 : +2 pts
            - Band Z < -0.20 : +1 pt
            - Volume Z > 2 : +2 pts
            - Volume Z > 3 : +1 pt
            - Wick Ratio ≥ 1.5 : +1 pt
            """)
        
        with col2:
            st.markdown("""
            **📈 Signaux Techniques**
            - RSI < 30 : +1 pt
            - Divergence RSI : +2 pts
            - Plus bas 30j : +1 pt
            - Plus bas 90j : +1 pt
            - Niveau psycho : +1 pt
            """)
        
        with col3:
            st.markdown("""
            **🎯 Classification**
            - Score ≥ 8 : **Major** 🔴
            - Score ≥ 6 : **Confirmé** 🟠
            - Score < 6 : **Simple** 🟡
            - Seuil recommandé : **≥ 6**
            """)
    
    # Initialiser l'analyseur
    analyzer = AdvancedBottomAnalyzer(df)
    
    # Paramètres dans la sidebar locale
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Paramètres Scoring")
    
    min_score = st.sidebar.slider(
        "Score minimum",
        min_value=4,
        max_value=9,
        value=6,
        help="Bottoms avec score ≥ seuil"
    )
    
    confirmation_window = st.sidebar.slider(
        "Fenêtre de confirmation",
        min_value=2,
        max_value=16,
        value=8,
        help="Bougies pour confirmer le bottom"
    )
    
    min_bounce = st.sidebar.slider(
        "Rebond minimum (%)",
        min_value=2,
        max_value=15,
        value=5,
        help="% de rebond pour confirmation"
    ) / 100
    
    # Détecter les bottoms avec scoring
    with st.spinner("Calcul des scores..."):
        bottoms_scored = analyzer.detect_bottoms_with_score(
            min_score=min_score,
            confirmation_window=confirmation_window,
            min_bounce=min_bounce
        )
    
    # Tabs pour différentes vues
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Scanner des Bottoms",
        "📈 Visualisation",
        "🔬 Backtest",
        "📉 Event Study"
    ])
    
    with tab1:
        display_bottom_scanner(bottoms_scored, analyzer, selected_tz_name)
    
    with tab2:
        display_scoring_charts(bottoms_scored, analyzer, df)
    
    with tab3:
        display_backtest_results(bottoms_scored, analyzer)
    
    with tab4:
        display_event_study(bottoms_scored, analyzer)

def display_bottom_scanner(bottoms_df, analyzer, selected_tz_name):
    """
    Affiche le scanner des bottoms avec leurs scores
    """
    st.subheader("📊 Scanner des Bottoms Scorés")
    
    if bottoms_df.empty:
        st.warning("Aucun bottom détecté avec les paramètres actuels")
        return
    
    # Statistiques générales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Bottoms", len(bottoms_df))
    
    with col2:
        avg_score = bottoms_df['score'].mean()
        st.metric("Score Moyen", f"{avg_score:.1f}/10")
    
    with col3:
        major_count = len(bottoms_df[bottoms_df['type'] == 'major'])
        st.metric("Bottoms Majeurs", major_count)
    
    with col4:
        avg_bounce = bottoms_df['bounce_pct'].mean()
        st.metric("Rebond Moyen", f"{avg_bounce:.1f}%")
    
    # Tableau détaillé
    st.subheader("🎯 Détail des Bottoms")
    
    # Préparer l'affichage
    display_df = bottoms_df.copy()
    display_df['Date'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
    display_df['Score'] = display_df['score'].apply(lambda x: f"{'⭐' * (x//2)}{'✨' * (x%2)} ({x}/10)")
    display_df['Type'] = display_df['type'].map({
        'major': '🔴 Majeur',
        'confirmed': '🟠 Confirmé',
        'simple': '🟡 Simple'
    })
    display_df['Prix'] = display_df['price'].apply(lambda x: f"${x:,.0f}")
    display_df['Band Z'] = display_df['band_z'].apply(lambda x: f"{x:.3f}")
    display_df['Vol Z'] = display_df['vol_z'].apply(lambda x: f"{x:.1f}")
    display_df['RSI'] = display_df['rsi'].apply(lambda x: f"{x:.0f}")
    display_df['Wick'] = display_df['wick_ratio'].apply(lambda x: f"{x:.1f}x")
    display_df['Rebond'] = display_df['bounce_pct'].apply(lambda x: f"{x:.1f}%")
    
    # Sélectionner les colonnes
    columns_to_show = ['Date', 'Score', 'Type', 'Prix', 'Band Z', 'Vol Z', 'RSI', 'Wick', 'Rebond']
    
    # Filtres
    col1, col2 = st.columns(2)
    
    with col1:
        type_filter = st.selectbox(
            "Filtrer par type",
            ["Tous", "Majeurs", "Confirmés", "Simples"]
        )
    
    with col2:
        sort_by = st.selectbox(
            "Trier par",
            ["Date (récent)", "Score (élevé)", "Band Z (extrême)", "Volume Z (élevé)"]
        )
    
    # Appliquer les filtres
    filtered_df = display_df.copy()
    
    if type_filter == "Majeurs":
        filtered_df = filtered_df[filtered_df['Type'] == '🔴 Majeur']
    elif type_filter == "Confirmés":
        filtered_df = filtered_df[filtered_df['Type'] == '🟠 Confirmé']
    elif type_filter == "Simples":
        filtered_df = filtered_df[filtered_df['Type'] == '🟡 Simple']
    
    # Appliquer le tri
    if sort_by == "Score (élevé)":
        filtered_df = filtered_df.sort_values('score', ascending=False)
    elif sort_by == "Band Z (extrême)":
        filtered_df = filtered_df.sort_values('band_z', ascending=True)
    elif sort_by == "Volume Z (élevé)":
        filtered_df = filtered_df.sort_values('vol_z', ascending=False)
    else:
        filtered_df = filtered_df.sort_values('timestamp', ascending=False)
    
    # Afficher le tableau
    st.dataframe(
        filtered_df[columns_to_show],
        use_container_width=True,
        height=500
    )
    
    # Export
    csv = filtered_df[columns_to_show].to_csv(index=False)
    st.download_button(
        label="📥 Télécharger les résultats",
        data=csv,
        file_name=f"bottoms_scored_{selected_tz_name}.csv",
        mime="text/csv"
    )

def display_scoring_charts(bottoms_df, analyzer, df):
    """
    Affiche les graphiques de scoring
    """
    st.subheader("📈 Visualisation des Signaux")
    
    if bottoms_df.empty:
        st.warning("Aucun bottom à visualiser")
        return
    
    # Graphique principal avec indicateurs
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.4, 0.2, 0.2, 0.2],
        subplot_titles=("Prix & Bollinger Bands", "Band Z-Score", "Volume Z-Score", "RSI")
    )
    
    # Prix et Bollinger Bands
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name="Prix",
            showlegend=False
        ),
        row=1, col=1
    )
    
    # Bollinger Bands
    fig.add_trace(
        go.Scatter(
            x=analyzer.df.index,
            y=analyzer.df['bb_high'],
            line=dict(color='gray', width=1),
            name='BB High',
            showlegend=False
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=analyzer.df.index,
            y=analyzer.df['bb_mid'],
            line=dict(color='blue', width=1, dash='dash'),
            name='BB Mid',
            showlegend=False
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=analyzer.df.index,
            y=analyzer.df['bb_low'],
            line=dict(color='gray', width=1),
            name='BB Low',
            fill='tonexty',
            fillcolor='rgba(128,128,128,0.1)',
            showlegend=False
        ),
        row=1, col=1
    )
    
    # Marquer les bottoms
    colors = {
        'major': 'red',
        'confirmed': 'orange',
        'simple': 'yellow'
    }
    
    for bottom_type in ['major', 'confirmed', 'simple']:
        type_bottoms = bottoms_df[bottoms_df['type'] == bottom_type]
        if not type_bottoms.empty:
            fig.add_trace(
                go.Scatter(
                    x=type_bottoms['timestamp'],
                    y=type_bottoms['price'],
                    mode='markers',
                    marker=dict(
                        size=12,
                        color=colors[bottom_type],
                        symbol='triangle-up',
                        line=dict(width=2, color='black')
                    ),
                    name=f"Bottom {bottom_type}",
                    text=type_bottoms['score'].apply(lambda x: f"Score: {x}"),
                    hovertemplate='%{text}<br>Prix: %{y}<extra></extra>'
                ),
                row=1, col=1
            )
    
    # Band Z-score
    fig.add_trace(
        go.Scatter(
            x=analyzer.df.index,
            y=analyzer.df['band_z'],
            line=dict(color='purple', width=1),
            name='Band Z',
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Ligne de seuil
    fig.add_hline(y=-0.1, line_dash="dash", line_color="orange", row=2, col=1)
    fig.add_hline(y=-0.2, line_dash="dash", line_color="red", row=2, col=1)
    
    # Volume Z-score
    fig.add_trace(
        go.Bar(
            x=analyzer.df.index,
            y=analyzer.df['vol_z'],
            marker_color='lightblue',
            name='Vol Z',
            showlegend=False
        ),
        row=3, col=1
    )
    
    fig.add_hline(y=2, line_dash="dash", line_color="orange", row=3, col=1)
    fig.add_hline(y=3, line_dash="dash", line_color="red", row=3, col=1)
    
    # RSI
    fig.add_trace(
        go.Scatter(
            x=analyzer.df.index,
            y=analyzer.df['rsi'],
            line=dict(color='green', width=1),
            name='RSI',
            showlegend=False
        ),
        row=4, col=1
    )
    
    fig.add_hline(y=30, line_dash="dash", line_color="red", row=4, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="blue", row=4, col=1)
    
    # Mise à jour du layout
    fig.update_layout(
        height=1000,
        showlegend=True,
        xaxis4_title="Date",
        yaxis1_title="Prix",
        yaxis2_title="Band Z",
        yaxis3_title="Vol Z",
        yaxis4_title="RSI"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Distribution des scores
    st.subheader("📊 Distribution des Scores")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_hist = px.histogram(
            bottoms_df,
            x='score',
            nbins=10,
            title="Distribution des Scores",
            labels={'score': 'Score', 'count': 'Nombre'},
            color_discrete_sequence=['#FF6B6B']
        )
        st.plotly_chart(fig_hist, use_container_width=True)
    
    with col2:
        fig_box = px.box(
            bottoms_df,
            y='bounce_pct',
            x='type',
            title="Rebond par Type de Bottom",
            labels={'bounce_pct': 'Rebond (%)', 'type': 'Type'},
            color='type',
            color_discrete_map={
                'major': '#FF0000',
                'confirmed': '#FFA500',
                'simple': '#FFFF00'
            }
        )
        st.plotly_chart(fig_box, use_container_width=True)

def display_backtest_results(bottoms_df, analyzer):
    """
    Affiche les résultats du backtest
    """
    st.subheader("🔬 Résultats du Backtest")
    
    if bottoms_df.empty:
        st.warning("Aucun bottom pour le backtest")
        return
    
    # Paramètres du backtest
    col1, col2, col3 = st.columns(3)
    
    with col1:
        stop_loss = st.number_input(
            "Stop Loss (points)",
            min_value=100,
            max_value=1000,
            value=300,
            step=50
        )
    
    with col2:
        tp_mode = st.selectbox(
            "Take Profit",
            ["BB Mid", "BB High", "3R", "5R", "10R"]
        )
    
    with col3:
        if st.button("🚀 Lancer Backtest", type="primary"):
            # Convertir le mode TP
            if tp_mode == "BB Mid":
                tp = 'bb_mid'
            elif tp_mode == "BB High":
                tp = 'bb_high'
            elif "R" in tp_mode:
                tp = float(tp_mode.replace("R", ""))
            
            # Lancer le backtest
            with st.spinner("Backtest en cours..."):
                metrics = analyzer.backtest_strategy(
                    bottoms_df,
                    stop_loss_points=stop_loss,
                    take_profit_mode=tp
                )
            
            # Afficher les résultats
            if metrics:
                st.success("Backtest terminé!")
                
                # Métriques principales
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Trades", metrics['total_trades'])
                    st.metric("Win Rate", f"{metrics['win_rate']:.1f}%")
                
                with col2:
                    st.metric("Expectancy", f"{metrics['expectancy']:.2f}%")
                    st.metric("Profit Factor", f"{metrics['profit_factor']:.2f}")
                
                with col3:
                    st.metric("Avg Win", f"{metrics['avg_win']:.2f}%")
                    st.metric("Avg Loss", f"{metrics['avg_loss']:.2f}%")
                
                with col4:
                    st.metric("Sharpe Ratio", f"{metrics['sharpe_ratio']:.2f}")
                    st.metric("Max DD", f"{metrics['max_drawdown']:.2f}")
                
                # Résultats par score
                st.subheader("📊 Performance par Score")
                
                if 'by_score' in metrics and not metrics['by_score'].empty:
                    score_df = metrics['by_score'].reset_index()
                    score_df.columns = ['Score', 'Trades', 'Avg Return', 'Std Dev']
                    
                    fig_score = px.bar(
                        score_df,
                        x='Score',
                        y='Avg Return',
                        title="Performance Moyenne par Score",
                        labels={'Avg Return': 'Retour Moyen (%)'},
                        color='Avg Return',
                        color_continuous_scale='RdYlGn'
                    )
                    st.plotly_chart(fig_score, use_container_width=True)
                
                # Résultats par type
                if 'by_type' in metrics and not metrics['by_type'].empty:
                    type_df = metrics['by_type'].reset_index()
                    type_df.columns = ['Type', 'Trades', 'Avg Return', 'Std Dev']
                    
                    st.dataframe(type_df, use_container_width=True)

def display_event_study(bottoms_df, analyzer):
    """
    Affiche l'analyse événementielle
    """
    st.subheader("📉 Event Study - Performance Post-Signal")
    
    if bottoms_df.empty:
        st.warning("Aucun bottom pour l'event study")
        return
    
    # Calculer les performances à différents horizons
    horizons = [4, 8, 24, 48, 96]  # En bougies (4h)
    results = []
    
    for idx, bottom in bottoms_df.iterrows():
        entry_idx = analyzer.df.index.get_loc(bottom['timestamp'])
        entry_price = bottom['close']
        
        perf_dict = {
            'score': bottom['score'],
            'type': bottom['type']
        }
        
        for horizon in horizons:
            if entry_idx + horizon < len(analyzer.df):
                future_price = analyzer.df['close'].iloc[entry_idx + horizon]
                perf = (future_price / entry_price - 1) * 100
                perf_dict[f'{horizon}b'] = perf
        
        results.append(perf_dict)
    
    perf_df = pd.DataFrame(results)
    
    # Afficher les statistiques moyennes
    st.subheader("📊 Performance Moyenne par Horizon")
    
    avg_perfs = []
    for horizon in horizons:
        col_name = f'{horizon}b'
        if col_name in perf_df.columns:
            avg_perfs.append({
                'Horizon': f"{horizon*4}h",
                'Perf Moy': perf_df[col_name].mean(),
                'Perf Med': perf_df[col_name].median(),
                'Win Rate': (perf_df[col_name] > 0).mean() * 100
            })
    
    avg_df = pd.DataFrame(avg_perfs)
    
    # Graphique
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=avg_df['Horizon'],
        y=avg_df['Perf Moy'],
        name='Performance Moyenne',
        marker_color='lightblue',
        text=avg_df['Perf Moy'].apply(lambda x: f"{x:.2f}%"),
        textposition='outside'
    ))
    
    fig.add_trace(go.Scatter(
        x=avg_df['Horizon'],
        y=avg_df['Win Rate'],
        name='Win Rate (%)',
        yaxis='y2',
        line=dict(color='green', width=2),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title="Performance Post-Bottom par Horizon",
        xaxis_title="Horizon Temporel",
        yaxis_title="Performance Moyenne (%)",
        yaxis2=dict(
            title="Win Rate (%)",
            overlaying='y',
            side='right'
        ),
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Tableau détaillé
    st.dataframe(
        avg_df.style.format({
            'Perf Moy': '{:.2f}%',
            'Perf Med': '{:.2f}%',
            'Win Rate': '{:.1f}%'
        }),
        use_container_width=True
    )