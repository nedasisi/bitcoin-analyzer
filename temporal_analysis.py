"""
Module d'analyse temporelle avancée des bottoms
Analyse détaillée par heure, jour, session de trading
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta

def create_temporal_analysis_tab(bottoms_tz, selected_tz_name, patterns, DAYS_FR):
    """
    Crée un onglet complet d'analyse temporelle
    """
    st.header(f"⏰ Analyse Temporelle Détaillée ({selected_tz_name})")
    
    if bottoms_tz.empty:
        st.warning("Aucun bottom détecté pour l'analyse")
        return
    
    # Sous-onglets pour différentes analyses
    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
        "📊 Analyse par Heure",
        "📅 Analyse Jour/Heure",
        "🌍 Sessions de Trading", 
        "📈 Tendances Temporelles"
    ])
    
    with sub_tab1:
        analyze_by_hour(bottoms_tz, selected_tz_name)
    
    with sub_tab2:
        analyze_day_hour_combination(bottoms_tz, selected_tz_name, DAYS_FR)
    
    with sub_tab3:
        analyze_trading_sessions(bottoms_tz, selected_tz_name)
    
    with sub_tab4:
        analyze_temporal_trends(bottoms_tz, selected_tz_name)

def analyze_by_hour(bottoms_tz, selected_tz_name):
    """
    Analyse détaillée par heure de la journée
    """
    st.subheader("📊 Distribution des Bottoms par Heure")
    
    # Calculer les statistiques par heure
    hourly_stats = bottoms_tz.groupby('hour').agg({
        'price': 'count',
        'strength': 'mean' if 'strength' in bottoms_tz.columns else lambda x: 1,
        'bounce_pct': 'mean' if 'bounce_pct' in bottoms_tz.columns else lambda x: 0
    }).round(2)
    
    hourly_stats.columns = ['count', 'avg_strength', 'avg_bounce']
    hourly_stats['percentage'] = (hourly_stats['count'] / hourly_stats['count'].sum() * 100).round(1)
    hourly_stats = hourly_stats.sort_values('count', ascending=False)
    
    # Graphique en barres principal
    fig_hourly = go.Figure()
    
    # Créer les données pour toutes les heures (0-23)
    all_hours = list(range(24))
    counts = [hourly_stats.loc[h, 'count'] if h in hourly_stats.index else 0 for h in all_hours]
    percentages = [hourly_stats.loc[h, 'percentage'] if h in hourly_stats.index else 0 for h in all_hours]
    
    # Déterminer les couleurs selon l'intensité
    max_count = max(counts) if counts else 1
    colors = ['rgba(255, 0, 0, {})'.format(0.3 + (c/max_count)*0.7) for c in counts]
    
    fig_hourly.add_trace(go.Bar(
        x=[f"{h:02d}:00" for h in all_hours],
        y=counts,
        text=[f"{c}<br>{p:.1f}%" if c > 0 else "" for c, p in zip(counts, percentages)],
        textposition='outside',
        marker_color=colors,
        hovertemplate='<b>%{x}</b><br>Bottoms: %{y}<br>%{text}<extra></extra>'
    ))
    
    fig_hourly.update_layout(
        title=f"Nombre de Bottoms par Heure ({selected_tz_name})",
        xaxis_title="Heure de la journée",
        yaxis_title="Nombre de bottoms",
        height=500,
        showlegend=False
    )
    
    st.plotly_chart(fig_hourly, use_container_width=True)
    
    # Top 5 et Bottom 5 heures
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔥 Top 5 Heures avec le Plus de Bottoms")
        top_5 = hourly_stats.nlargest(5, 'count')
        
        for idx, (hour, row) in enumerate(top_5.iterrows(), 1):
            medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "🏅"
            st.markdown(f"""
            {medal} **{hour:02d}:00** - {int(row['count'])} bottoms ({row['percentage']:.1f}%)
            """)
            
            # Barre de progression visuelle
            st.progress(row['count'] / hourly_stats['count'].max())
    
    with col2:
        st.markdown("### 💚 Top 5 Heures les Plus Sûres")
        bottom_5 = hourly_stats.nsmallest(5, 'count')
        
        for hour, row in bottom_5.iterrows():
            st.markdown(f"""
            ✅ **{hour:02d}:00** - {int(row['count'])} bottoms ({row['percentage']:.1f}%)
            """)
    
    # Graphique radial (horloge)
    st.subheader("🕐 Vue Horloge des Bottoms")
    
    fig_clock = go.Figure()
    
    # Préparer les données pour le graphique radial
    theta = [h * 15 for h in all_hours]  # Convertir heures en degrés (360/24 = 15)
    
    fig_clock.add_trace(go.Scatterpolar(
        r=counts,
        theta=theta,
        fill='toself',
        fillcolor='rgba(255, 0, 0, 0.3)',
        line=dict(color='red', width=2),
        marker=dict(size=8, color='darkred'),
        text=[f"{h:02d}:00<br>{c} bottoms" for h, c in zip(all_hours, counts)],
        hoverinfo='text'
    ))
    
    fig_clock.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                showgrid=True,
                gridcolor='lightgray',
                range=[0, max(counts) * 1.1] if counts else [0, 1]
            ),
            angularaxis=dict(
                tickmode='array',
                tickvals=theta,
                ticktext=[f"{h:02d}h" for h in all_hours],
                direction='clockwise',
                rotation=90
            )
        ),
        showlegend=False,
        title=f"Distribution en Horloge ({selected_tz_name})",
        height=500
    )
    
    st.plotly_chart(fig_clock, use_container_width=True)
    
    # Statistiques détaillées
    st.subheader("📊 Statistiques Détaillées par Heure")
    
    # Ajouter des indicateurs visuels
    display_stats = hourly_stats.copy()
    display_stats['Heure'] = [f"{h:02d}:00" for h in display_stats.index]
    display_stats['Bottoms'] = display_stats['count'].astype(int)
    display_stats['%'] = display_stats['percentage'].apply(lambda x: f"{x:.1f}%")
    
    if 'avg_strength' in display_stats.columns:
        display_stats['Force Moy'] = display_stats['avg_strength'].apply(lambda x: '⭐' * int(x) if x > 0 else 'N/A')
    
    if 'avg_bounce' in display_stats.columns and display_stats['avg_bounce'].sum() > 0:
        display_stats['Rebond Moy'] = display_stats['avg_bounce'].apply(lambda x: f"{x:.1f}%" if x > 0 else 'N/A')
    
    # Sélectionner les colonnes à afficher
    cols_to_show = ['Heure', 'Bottoms', '%']
    if 'Force Moy' in display_stats.columns:
        cols_to_show.append('Force Moy')
    if 'Rebond Moy' in display_stats.columns:
        cols_to_show.append('Rebond Moy')
    
    st.dataframe(
        display_stats[cols_to_show].sort_values('Bottoms', ascending=False),
        use_container_width=True,
        height=400
    )

def analyze_day_hour_combination(bottoms_tz, selected_tz_name, DAYS_FR):
    """
    Analyse croisée jour/heure
    """
    st.subheader("📅 Analyse Croisée Jour × Heure")
    
    # Créer la matrice jour/heure
    pivot_table = bottoms_tz.pivot_table(
        index='day_of_week',
        columns='hour',
        values='price',
        aggfunc='count',
        fill_value=0
    )
    
    # Renommer les jours
    pivot_table.index = [DAYS_FR[i] for i in pivot_table.index]
    
    # Heatmap interactive
    fig_heatmap = go.Figure(data=go.Heatmap(
        z=pivot_table.values,
        x=[f"{h:02d}:00" for h in pivot_table.columns],
        y=pivot_table.index,
        colorscale='Reds',
        text=pivot_table.values,
        texttemplate='%{text}',
        textfont={"size": 10},
        hovertemplate='<b>%{y}</b><br>%{x}<br>Bottoms: %{z}<extra></extra>',
        colorbar=dict(title="Nombre<br>de bottoms")
    ))
    
    fig_heatmap.update_layout(
        title=f"Heatmap des Bottoms par Jour et Heure ({selected_tz_name})",
        xaxis_title="Heure de la journée",
        yaxis_title="Jour de la semaine",
        height=500
    )
    
    st.plotly_chart(fig_heatmap, use_container_width=True)
    
    # Meilleurs créneaux
    st.subheader("🎯 Meilleurs Créneaux Horaires")
    
    # Trouver les top créneaux
    top_slots = []
    for day in pivot_table.index:
        for hour in pivot_table.columns:
            count = pivot_table.loc[day, hour]
            if count > 0:
                top_slots.append({
                    'Jour': day,
                    'Heure': f"{hour:02d}:00",
                    'Bottoms': int(count)
                })
    
    top_slots_df = pd.DataFrame(top_slots).sort_values('Bottoms', ascending=False).head(10)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔴 Top 10 Créneaux à Risque")
        for idx, row in top_slots_df.iterrows():
            st.markdown(f"**{row['Jour']} {row['Heure']}** - {row['Bottoms']} bottoms")
    
    with col2:
        st.markdown("### 💡 Insights")
        
        # Calculer le jour avec le plus de bottoms
        best_day = pivot_table.sum(axis=1).idxmax()
        worst_day = pivot_table.sum(axis=1).idxmin()
        
        # Calculer l'heure avec le plus de bottoms
        best_hour = pivot_table.sum(axis=0).idxmax()
        worst_hour = pivot_table.sum(axis=0).idxmin()
        
        st.info(f"""
        **Analyse des Patterns:**
        
        📅 **Jour le plus risqué**: {best_day}
        ✅ **Jour le plus sûr**: {worst_day}
        
        🕐 **Heure la plus risquée**: {best_hour:02d}:00
        ✅ **Heure la plus sûre**: {worst_hour:02d}:00
        
        🎯 **Créneau le plus dangereux**: 
        {top_slots_df.iloc[0]['Jour']} à {top_slots_df.iloc[0]['Heure']}
        """)

def analyze_trading_sessions(bottoms_tz, selected_tz_name):
    """
    Analyse par session de trading
    """
    st.subheader("🌍 Analyse par Session de Trading")
    
    # Définir les sessions selon le fuseau
    sessions = define_trading_sessions(selected_tz_name)
    
    # Classifier les bottoms par session
    def classify_session(hour):
        for session_name, (start, end) in sessions.items():
            if start <= end:
                if start <= hour < end:
                    return session_name
            else:  # Session qui traverse minuit
                if hour >= start or hour < end:
                    return session_name
        return "Autre"
    
    bottoms_tz['session'] = bottoms_tz['hour'].apply(classify_session)
    
    # Statistiques par session
    session_stats = bottoms_tz.groupby('session').agg({
        'price': 'count',
        'strength': 'mean' if 'strength' in bottoms_tz.columns else lambda x: 1,
        'bounce_pct': 'mean' if 'bounce_pct' in bottoms_tz.columns else lambda x: 0
    }).round(2)
    
    session_stats.columns = ['count', 'avg_strength', 'avg_bounce']
    session_stats['percentage'] = (session_stats['count'] / session_stats['count'].sum() * 100).round(1)
    
    # Graphique en camembert
    fig_pie = px.pie(
        values=session_stats['count'],
        names=session_stats.index,
        title=f"Répartition des Bottoms par Session ({selected_tz_name})",
        color_discrete_map={
            'Asie': '#FF6B6B',
            'Europe': '#4ECDC4',
            'US': '#45B7D1',
            'Weekend': '#96CEB4'
        }
    )
    
    fig_pie.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>Bottoms: %{value}<br>%{percent}<extra></extra>'
    )
    
    st.plotly_chart(fig_pie, use_container_width=True)
    
    # Barres comparatives
    col1, col2 = st.columns(2)
    
    with col1:
        fig_bars = go.Figure()
        
        fig_bars.add_trace(go.Bar(
            x=session_stats.index,
            y=session_stats['count'],
            text=session_stats['count'],
            textposition='auto',
            marker_color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'][:len(session_stats)]
        ))
        
        fig_bars.update_layout(
            title="Nombre de Bottoms par Session",
            xaxis_title="Session",
            yaxis_title="Nombre de bottoms",
            showlegend=False,
            height=400
        )
        
        st.plotly_chart(fig_bars, use_container_width=True)
    
    with col2:
        # Tableau récapitulatif
        st.markdown("### 📊 Statistiques par Session")
        
        display_session = session_stats.copy()
        display_session['Session'] = display_session.index
        display_session['Bottoms'] = display_session['count'].astype(int)
        display_session['%'] = display_session['percentage'].apply(lambda x: f"{x:.1f}%")
        
        if 'avg_strength' in display_session.columns:
            display_session['Force'] = display_session['avg_strength'].apply(lambda x: '⭐' * int(x))
        
        st.dataframe(
            display_session[['Session', 'Bottoms', '%', 'Force']],
            use_container_width=True,
            hide_index=True
        )
    
    # Recommandations par session
    st.subheader("💡 Recommandations par Session")
    
    most_risky_session = session_stats['count'].idxmax()
    safest_session = session_stats['count'].idxmin()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.error(f"""
        🔴 **Session la Plus Risquée**
        
        **{most_risky_session}**
        - {session_stats.loc[most_risky_session, 'count']:.0f} bottoms
        - {session_stats.loc[most_risky_session, 'percentage']:.1f}% du total
        """)
    
    with col2:
        st.success(f"""
        ✅ **Session la Plus Sûre**
        
        **{safest_session}**
        - {session_stats.loc[safest_session, 'count']:.0f} bottoms
        - {session_stats.loc[safest_session, 'percentage']:.1f}% du total
        """)
    
    with col3:
        st.info(f"""
        📊 **Stratégie Suggérée**
        
        - Éviter les entrées: **{most_risky_session}**
        - Privilégier: **{safest_session}**
        - DCA optimal: Hors sessions à risque
        """)

def analyze_temporal_trends(bottoms_tz, selected_tz_name):
    """
    Analyse des tendances temporelles
    """
    st.subheader("📈 Tendances et Évolutions Temporelles")
    
    # Évolution par mois
    monthly_bottoms = bottoms_tz.groupby(pd.Grouper(freq='ME')).size()
    
    fig_monthly = go.Figure()
    
    fig_monthly.add_trace(go.Scatter(
        x=monthly_bottoms.index,
        y=monthly_bottoms.values,
        mode='lines+markers',
        line=dict(color='red', width=2),
        marker=dict(size=8, color='darkred'),
        fill='tozeroy',
        fillcolor='rgba(255, 0, 0, 0.1)'
    ))
    
    # Ajouter une ligne de tendance
    z = np.polyfit(range(len(monthly_bottoms)), monthly_bottoms.values, 1)
    p = np.poly1d(z)
    
    fig_monthly.add_trace(go.Scatter(
        x=monthly_bottoms.index,
        y=p(range(len(monthly_bottoms))),
        mode='lines',
        line=dict(color='blue', width=2, dash='dash'),
        name='Tendance'
    ))
    
    fig_monthly.update_layout(
        title=f"Évolution Mensuelle des Bottoms ({selected_tz_name})",
        xaxis_title="Date",
        yaxis_title="Nombre de bottoms",
        showlegend=True,
        height=400
    )
    
    st.plotly_chart(fig_monthly, use_container_width=True)
    
    # Analyse par trimestre
    col1, col2 = st.columns(2)
    
    with col1:
        # Bottoms par trimestre
        bottoms_tz['quarter'] = bottoms_tz.index.quarter
        quarterly_stats = bottoms_tz.groupby('quarter').size()
        
        fig_quarter = go.Figure(go.Bar(
            x=['Q1', 'Q2', 'Q3', 'Q4'],
            y=quarterly_stats.values,
            marker_color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'],
            text=quarterly_stats.values,
            textposition='auto'
        ))
        
        fig_quarter.update_layout(
            title="Répartition par Trimestre",
            xaxis_title="Trimestre",
            yaxis_title="Nombre de bottoms",
            height=350
        )
        
        st.plotly_chart(fig_quarter, use_container_width=True)
    
    with col2:
        # Bottoms par année
        yearly_stats = bottoms_tz.groupby(bottoms_tz.index.year).size()
        
        fig_year = go.Figure(go.Bar(
            x=yearly_stats.index,
            y=yearly_stats.values,
            marker_color='lightcoral',
            text=yearly_stats.values,
            textposition='auto'
        ))
        
        fig_year.update_layout(
            title="Évolution Annuelle",
            xaxis_title="Année",
            yaxis_title="Nombre de bottoms",
            height=350
        )
        
        st.plotly_chart(fig_year, use_container_width=True)
    
    # Insights temporels
    st.subheader("🎯 Insights Temporels Clés")
    
    # Calculer les statistiques
    most_active_month = monthly_bottoms.idxmax()
    least_active_month = monthly_bottoms.idxmin()
    avg_monthly = monthly_bottoms.mean()
    
    most_active_year = yearly_stats.idxmax()
    least_active_year = yearly_stats.idxmin()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Mois le Plus Actif",
            most_active_month.strftime('%B %Y'),
            f"{monthly_bottoms.max():.0f} bottoms"
        )
    
    with col2:
        st.metric(
            "Moyenne Mensuelle",
            f"{avg_monthly:.1f} bottoms",
            f"Total: {monthly_bottoms.sum():.0f}"
        )
    
    with col3:
        st.metric(
            "Année la Plus Volatile",
            str(most_active_year),
            f"{yearly_stats.max():.0f} bottoms"
        )

def define_trading_sessions(timezone_name):
    """
    Définit les sessions de trading selon le fuseau horaire
    """
    if "Paris" in timezone_name or "Europe" in timezone_name:
        return {
            'Asie': (1, 9),
            'Europe': (9, 17),
            'US': (17, 1)
        }
    elif "Bangkok" in timezone_name or "Asia" in timezone_name:
        return {
            'Asie': (7, 15),
            'Europe': (15, 23),
            'US': (23, 7)
        }
    elif "New_York" in timezone_name or "America" in timezone_name:
        return {
            'Asie': (19, 3),
            'Europe': (3, 11),
            'US': (11, 19)
        }
    else:  # UTC
        return {
            'Asie': (0, 8),
            'Europe': (8, 16),
            'US': (16, 0)
        }