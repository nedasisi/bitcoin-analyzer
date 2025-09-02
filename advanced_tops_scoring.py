"""
Système de Scoring Avancé pour les Tops
Analyse multi-critères avec score de 0 à 10
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

class TopScoringSystem:
    """
    Système de scoring avancé pour évaluer la qualité et la fiabilité des tops
    """
    
    def __init__(self):
        self.weights = {
            'technical': 0.30,    # Indicateurs techniques (RSI, BB, divergences)
            'volume': 0.20,       # Analyse du volume
            'pattern': 0.20,      # Pattern de prix (double top, etc.)
            'temporal': 0.15,     # Timing (heure/jour)
            'market': 0.15        # Contexte de marché
        }
    
    def calculate_top_score(self, top_data, df, all_tops):
        """
        Calcule un score de 0 à 10 pour un top donné
        
        Args:
            top_data: Données du top à analyser
            df: DataFrame complet des prix
            all_tops: Tous les tops détectés
        
        Returns:
            dict avec score total et détails
        """
        scores = {}
        
        # 1. Score Technique (0-10)
        scores['technical'] = self._calculate_technical_score(top_data, df)
        
        # 2. Score Volume (0-10)
        scores['volume'] = self._calculate_volume_score(top_data, df)
        
        # 3. Score Pattern (0-10)
        scores['pattern'] = self._calculate_pattern_score(top_data, df)
        
        # 4. Score Temporel (0-10)
        scores['temporal'] = self._calculate_temporal_score(top_data, all_tops)
        
        # 5. Score Marché (0-10)
        scores['market'] = self._calculate_market_score(top_data, df)
        
        # Score total pondéré
        total_score = sum(scores[k] * self.weights[k] for k in scores)
        
        return {
            'total_score': round(total_score, 2),
            'scores': scores,
            'confidence': self._get_confidence_level(total_score),
            'recommendation': self._get_recommendation(total_score)
        }
    
    def _calculate_technical_score(self, top_data, df):
        """Score basé sur les indicateurs techniques"""
        score = 5.0  # Base
        
        # RSI
        if 'rsi' in top_data and pd.notna(top_data['rsi']):
            rsi = top_data['rsi']
            if rsi >= 80:
                score += 2.0  # RSI très élevé
            elif rsi >= 70:
                score += 1.0  # RSI élevé
            elif rsi < 50:
                score -= 2.0  # RSI faible pour un top
        
        # Bollinger Bands
        if 'bb_pct' in top_data and pd.notna(top_data['bb_pct']):
            bb_pct = top_data['bb_pct']
            if bb_pct >= 1.0:
                score += 1.5  # Au-dessus de la bande haute
            elif bb_pct >= 0.95:
                score += 0.5  # Proche de la bande haute
            elif bb_pct < 0.5:
                score -= 1.0  # Loin de la bande haute
        
        # Divergence (si disponible)
        if 'divergence' in top_data:
            if top_data['divergence'] == 'bearish':
                score += 1.5  # Divergence baissière
        
        return max(0, min(10, score))
    
    def _calculate_volume_score(self, top_data, df):
        """Score basé sur l'analyse du volume"""
        score = 5.0
        
        if 'volume_ratio' in top_data and pd.notna(top_data['volume_ratio']):
            vol_ratio = top_data['volume_ratio']
            
            if vol_ratio >= 3.0:
                score += 3.0  # Volume exceptionnel
            elif vol_ratio >= 2.0:
                score += 2.0  # Volume très élevé
            elif vol_ratio >= 1.5:
                score += 1.0  # Volume élevé
            elif vol_ratio < 0.8:
                score -= 2.0  # Volume faible
        
        # Pattern de volume (climax)
        if 'volume_pattern' in top_data:
            if top_data['volume_pattern'] == 'climax':
                score += 2.0  # Volume climax
        
        return max(0, min(10, score))
    
    def _calculate_pattern_score(self, top_data, df):
        """Score basé sur les patterns de prix"""
        score = 5.0
        
        # Type de top
        if 'type' in top_data:
            if top_data['type'] == 'major':
                score += 2.0
            elif top_data['type'] == 'confirmed':
                score += 1.0
        
        # Amplitude de la montée avant
        if 'rise_pct' in top_data and pd.notna(top_data['rise_pct']):
            rise = top_data['rise_pct']
            if rise >= 100:
                score += 2.0  # Montée parabolique
            elif rise >= 50:
                score += 1.0
            elif rise < 20:
                score -= 1.0
        
        # Chute après (validation)
        if 'drop_pct' in top_data and pd.notna(top_data['drop_pct']):
            drop = top_data['drop_pct']
            if drop >= 20:
                score += 1.0  # Chute confirmée
            elif drop < 5:
                score -= 2.0  # Pas de chute = pas un vrai top
        
        return max(0, min(10, score))
    
    def _calculate_temporal_score(self, top_data, all_tops):
        """Score basé sur le timing"""
        score = 5.0
        
        # Heure du top
        hour = top_data.get('hour', 12)
        
        # Heures typiques de tops (basé sur l'analyse historique)
        peak_hours = [10, 11, 12, 13, 14, 15, 16]  # Heures Europe/US
        if hour in peak_hours:
            score += 1.5
        
        # Jour de la semaine
        day = top_data.get('day_of_week', 0)
        
        # Jours typiques de tops
        if day in [2, 3, 4]:  # Milieu de semaine
            score += 1.0
        elif day in [0, 6]:  # Lundi ou Dimanche
            score -= 0.5
        
        # Distance au top précédent
        if hasattr(top_data, 'name') and not all_tops.empty:
            current_time = top_data.name
            previous_tops = all_tops[all_tops.index < current_time]
            
            if not previous_tops.empty:
                last_top = previous_tops.index[-1]
                days_since = (current_time - last_top).days
                
                if days_since > 90:
                    score += 2.0  # Long temps sans top
                elif days_since > 30:
                    score += 1.0
                elif days_since < 7:
                    score -= 1.0  # Trop proche du précédent
        
        return max(0, min(10, score))
    
    def _calculate_market_score(self, top_data, df):
        """Score basé sur le contexte de marché"""
        score = 5.0
        
        # Position dans le range historique
        if 'price' in top_data:
            price = top_data['price']
            
            # Calculer le percentile du prix
            if len(df) > 100:
                percentile = (df['close'] < price).sum() / len(df) * 100
                
                if percentile >= 95:
                    score += 2.0  # Dans les 5% plus hauts historiques
                elif percentile >= 90:
                    score += 1.0
                elif percentile < 50:
                    score -= 2.0  # Pas vraiment un top si dans la moitié basse
        
        # Momentum du marché
        if 'market_momentum' in top_data:
            if top_data['market_momentum'] == 'exhausted':
                score += 1.5
            elif top_data['market_momentum'] == 'strong':
                score -= 1.0
        
        # Sentiment (si disponible)
        if 'fear_greed_index' in top_data:
            fgi = top_data['fear_greed_index']
            if fgi >= 80:
                score += 2.0  # Extreme Greed
            elif fgi >= 70:
                score += 1.0
            elif fgi < 30:
                score -= 2.0  # Fear = pas un top
        
        return max(0, min(10, score))
    
    def _get_confidence_level(self, score):
        """Détermine le niveau de confiance"""
        if score >= 8:
            return "🔴 TRÈS ÉLEVÉ"
        elif score >= 7:
            return "🟠 ÉLEVÉ"
        elif score >= 6:
            return "🟡 MOYEN"
        elif score >= 5:
            return "🟢 FAIBLE"
        else:
            return "⚪ TRÈS FAIBLE"
    
    def _get_recommendation(self, score):
        """Génère une recommandation basée sur le score"""
        if score >= 8:
            return "⚠️ TOP MAJEUR PROBABLE - Forte probabilité de retournement. Considérer prise de profits ou short."
        elif score >= 7:
            return "📊 TOP CONFIRMÉ - Signal de prudence. Réduire l'exposition ou serrer les stops."
        elif score >= 6:
            return "👀 TOP POSSIBLE - Surveiller de près. Préparer une stratégie de sortie."
        elif score >= 5:
            return "📈 MOMENTUM INTACT - Possibilité de continuation. Rester vigilant."
        else:
            return "✅ PAS DE SIGNAL TOP - Peu de risque immédiat de retournement."
    
    def analyze_all_tops(self, tops_df, price_df):
        """
        Analyse tous les tops et calcule leurs scores
        
        Args:
            tops_df: DataFrame des tops
            price_df: DataFrame des prix
        
        Returns:
            DataFrame enrichi avec les scores
        """
        scored_tops = []
        
        for idx, top in tops_df.iterrows():
            score_data = self.calculate_top_score(top, price_df, tops_df)
            
            scored_top = {
                'timestamp': idx,
                'price': top['price'],
                'type': top.get('type', 'simple'),
                'score': score_data['total_score'],
                'confidence': score_data['confidence'],
                'technical_score': score_data['scores']['technical'],
                'volume_score': score_data['scores']['volume'],
                'pattern_score': score_data['scores']['pattern'],
                'temporal_score': score_data['scores']['temporal'],
                'market_score': score_data['scores']['market'],
                'recommendation': score_data['recommendation']
            }
            
            scored_tops.append(scored_top)
        
        return pd.DataFrame(scored_tops)


def create_advanced_tops_scoring_tab(df, tops, selected_tz_name):
    """
    Crée l'onglet de scoring avancé pour les tops
    """
    st.header(f"🎯 Système de Scoring Avancé des Tops - {selected_tz_name}")
    
    # Initialiser le système de scoring
    scoring_system = TopScoringSystem()
    
    # Calculer les scores pour tous les tops
    if not tops.empty:
        with st.spinner("Calcul des scores en cours..."):
            scored_tops = scoring_system.analyze_all_tops(tops, df)
            
            # Trier par score décroissant
            scored_tops = scored_tops.sort_values('score', ascending=False)
        
        # Afficher les métriques principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            top_scores = scored_tops[scored_tops['score'] >= 8]
            st.metric("Tops Majeurs (Score ≥ 8)", len(top_scores))
        
        with col2:
            avg_score = scored_tops['score'].mean()
            st.metric("Score Moyen", f"{avg_score:.2f}/10")
        
        with col3:
            best_top = scored_tops.iloc[0] if not scored_tops.empty else None
            if best_top is not None:
                st.metric("Meilleur Score", f"{best_top['score']:.2f}/10")
        
        with col4:
            recent_tops = scored_tops.head(10)
            recent_avg = recent_tops['score'].mean()
            st.metric("Score Moy (10 récents)", f"{recent_avg:.2f}/10")
        
        # Sous-onglets pour différentes vues
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🏆 Top Scores",
            "📊 Analyse Détaillée",
            "📈 Évolution",
            "🎯 Recommandations",
            "📋 Export"
        ])
        
        with tab1:
            display_top_scores(scored_tops, selected_tz_name)
        
        with tab2:
            display_detailed_analysis(scored_tops, df, selected_tz_name)
        
        with tab3:
            display_score_evolution(scored_tops, selected_tz_name)
        
        with tab4:
            display_recommendations(scored_tops, df, selected_tz_name)
        
        with tab5:
            export_scored_tops(scored_tops, selected_tz_name)
    
    else:
        st.warning("Aucun top détecté pour l'analyse")


def display_top_scores(scored_tops, tz_name):
    """Affiche le classement des meilleurs tops"""
    
    st.subheader("🏆 Classement des Tops par Score")
    
    # Top 10 des meilleurs scores
    top_10 = scored_tops.head(10)
    
    # Créer un DataFrame d'affichage
    display_df = pd.DataFrame({
        'Rang': range(1, len(top_10) + 1),
        'Date': pd.to_datetime(top_10['timestamp']).dt.strftime('%Y-%m-%d %H:%M'),
        'Prix': top_10['price'].apply(lambda x: f"${x:,.0f}"),
        'Score': top_10['score'].apply(lambda x: f"{x:.2f}/10"),
        'Confiance': top_10['confidence'],
        'Type': top_10['type'].map({
            'simple': '🟡 Simple',
            'confirmed': '🟠 Confirmé',
            'major': '🔴 Majeur'
        })
    })
    
    # Afficher avec couleurs selon le score
    st.dataframe(
        display_df,
        use_container_width=True,
        height=400
    )
    
    # Graphique des scores
    fig = px.bar(
        top_10,
        x=pd.to_datetime(top_10['timestamp']).dt.strftime('%Y-%m-%d'),
        y='score',
        color='score',
        color_continuous_scale='RdYlGn_r',
        title="Top 10 des Meilleurs Scores",
        labels={'score': 'Score (/10)', 'x': 'Date'}
    )
    
    fig.add_hline(y=8, line_dash="dash", line_color="red", 
                  annotation_text="Seuil Top Majeur")
    fig.add_hline(y=7, line_dash="dash", line_color="orange",
                  annotation_text="Seuil Top Confirmé")
    
    st.plotly_chart(fig, use_container_width=True)


def display_detailed_analysis(scored_tops, df, tz_name):
    """Analyse détaillée des composants du score"""
    
    st.subheader("📊 Analyse Détaillée des Scores")
    
    # Sélecteur de top à analyser
    selected_date = st.selectbox(
        "Sélectionner un top à analyser",
        scored_tops['timestamp'].dt.strftime('%Y-%m-%d %H:%M').tolist()
    )
    
    # Récupérer le top sélectionné
    selected_top = scored_tops[
        scored_tops['timestamp'].dt.strftime('%Y-%m-%d %H:%M') == selected_date
    ].iloc[0]
    
    # Afficher le score total
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Score Total", f"{selected_top['score']:.2f}/10")
    with col2:
        st.metric("Confiance", selected_top['confidence'])
    with col3:
        st.metric("Prix", f"${selected_top['price']:,.0f}")
    
    # Décomposition du score
    st.subheader("🔍 Décomposition du Score")
    
    # Créer un graphique radar
    categories = ['Technique', 'Volume', 'Pattern', 'Temporel', 'Marché']
    values = [
        selected_top['technical_score'],
        selected_top['volume_score'],
        selected_top['pattern_score'],
        selected_top['temporal_score'],
        selected_top['market_score']
    ]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        fillcolor='rgba(255, 0, 0, 0.3)',
        line=dict(color='red', width=2),
        marker=dict(size=8, color='darkred'),
        name='Score'
    ))
    
    # Ajouter le maximum (10)
    fig.add_trace(go.Scatterpolar(
        r=[10, 10, 10, 10, 10],
        theta=categories,
        line=dict(color='gray', width=1, dash='dash'),
        name='Maximum'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 10]
            )
        ),
        title=f"Analyse Multi-Critères - {selected_date}",
        showlegend=True
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Détails des scores
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Scores Détaillés")
        scores_df = pd.DataFrame({
            'Critère': categories,
            'Score': values,
            'Poids': ['30%', '20%', '20%', '15%', '15%']
        })
        st.dataframe(scores_df, use_container_width=True)
    
    with col2:
        st.markdown("### 💡 Recommandation")
        st.info(selected_top['recommendation'])


def display_score_evolution(scored_tops, tz_name):
    """Évolution des scores dans le temps"""
    
    st.subheader("📈 Évolution des Scores dans le Temps")
    
    # Trier par date
    scored_tops = scored_tops.sort_values('timestamp')
    
    # Graphique d'évolution
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=("Score des Tops", "Distribution des Scores")
    )
    
    # Ligne de score
    fig.add_trace(
        go.Scatter(
            x=scored_tops['timestamp'],
            y=scored_tops['score'],
            mode='lines+markers',
            line=dict(color='red', width=2),
            marker=dict(
                size=8,
                color=scored_tops['score'],
                colorscale='RdYlGn_r',
                showscale=True,
                colorbar=dict(title="Score", y=0.8)
            ),
            name='Score'
        ),
        row=1, col=1
    )
    
    # Zones de score
    fig.add_hrect(y0=8, y1=10, fillcolor="red", opacity=0.1, row=1, col=1)
    fig.add_hrect(y0=7, y1=8, fillcolor="orange", opacity=0.1, row=1, col=1)
    fig.add_hrect(y0=6, y1=7, fillcolor="yellow", opacity=0.1, row=1, col=1)
    
    # Histogramme
    fig.add_trace(
        go.Histogram(
            x=scored_tops['score'],
            nbinsx=20,
            marker_color='red',
            name='Distribution'
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        height=700,
        title=f"Évolution et Distribution des Scores ({tz_name})",
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Statistiques temporelles
    st.subheader("📊 Statistiques Temporelles")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Moyenne mobile
        window = st.slider("Fenêtre moyenne mobile (tops)", 5, 50, 20)
        scored_tops['ma_score'] = scored_tops['score'].rolling(window=window).mean()
        
        fig_ma = go.Figure()
        fig_ma.add_trace(go.Scatter(
            x=scored_tops['timestamp'],
            y=scored_tops['ma_score'],
            mode='lines',
            line=dict(color='red', width=2),
            name=f'MA{window}'
        ))
        
        fig_ma.update_layout(
            title=f"Moyenne Mobile des Scores (MA{window})",
            height=300
        )
        
        st.plotly_chart(fig_ma, use_container_width=True)
    
    with col2:
        # Tendance
        recent_avg = scored_tops.tail(10)['score'].mean()
        older_avg = scored_tops.head(10)['score'].mean()
        
        trend = "📈 Hausse" if recent_avg > older_avg else "📉 Baisse"
        st.metric("Tendance des Scores", trend, f"{recent_avg - older_avg:+.2f}")
        
        # Périodes à risque
        high_risk = scored_tops[scored_tops['score'] >= 8]
        st.metric("Périodes Haut Risque", f"{len(high_risk)} tops")
    
    with col3:
        # Cycles
        st.markdown("### 🔄 Analyse des Cycles")
        
        # Calculer les intervalles entre tops majeurs
        major_tops = scored_tops[scored_tops['score'] >= 8]
        if len(major_tops) > 1:
            intervals = major_tops['timestamp'].diff().dt.days.dropna()
            avg_cycle = intervals.mean()
            st.metric("Cycle Moyen (jours)", f"{avg_cycle:.0f}")
        else:
            st.info("Pas assez de tops majeurs pour calculer les cycles")


def display_recommendations(scored_tops, df, tz_name):
    """Affiche les recommandations basées sur l'analyse"""
    
    st.subheader("🎯 Recommandations Stratégiques")
    
    # Analyse du contexte actuel
    current_price = df['close'].iloc[-1]
    last_top = scored_tops.iloc[0] if not scored_tops.empty else None
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Contexte Actuel")
        
        if last_top is not None:
            days_since = (datetime.now(last_top['timestamp'].tzinfo) - last_top['timestamp']).days
            price_change = ((current_price - last_top['price']) / last_top['price']) * 100
            
            st.metric("Dernier Top Score Élevé", f"Il y a {days_since} jours")
            st.metric("Variation depuis", f"{price_change:+.2f}%")
            
            if last_top['score'] >= 8 and days_since < 30:
                st.warning("⚠️ Top majeur récent - Prudence recommandée")
            elif days_since > 90:
                st.info("✅ Pas de top majeur récent")
    
    with col2:
        st.markdown("### 💡 Stratégies Suggérées")
        
        # Analyser les tops récents
        recent_tops = scored_tops.head(5)
        avg_recent_score = recent_tops['score'].mean() if not recent_tops.empty else 0
        
        if avg_recent_score >= 7:
            st.error("""
            **🔴 SIGNAL DE PRUDENCE ÉLEVÉ**
            - Réduire l'exposition long
            - Considérer des prises de profit
            - Préparer stratégies de short
            - Serrer les stop-loss
            """)
        elif avg_recent_score >= 6:
            st.warning("""
            **🟠 VIGILANCE RECOMMANDÉE**
            - Surveiller les indicateurs
            - Préparer plans de sortie
            - Éviter nouveaux longs
            - Garder liquidités disponibles
            """)
        else:
            st.success("""
            **🟢 RISQUE MODÉRÉ**
            - Stratégies long possibles
            - Rester vigilant sur volumes
            - DCA possible sur corrections
            - Surveiller RSI et divergences
            """)
    
    # Tops à surveiller
    st.markdown("### 👀 Niveaux à Surveiller")
    
    # Identifier les zones de résistance basées sur les tops majeurs
    major_tops = scored_tops[scored_tops['score'] >= 7].head(5)
    
    if not major_tops.empty:
        resistance_levels = major_tops[['timestamp', 'price', 'score']].copy()
        resistance_levels['niveau'] = resistance_levels['price'].apply(lambda x: f"${x:,.0f}")
        resistance_levels['force'] = resistance_levels['score'].apply(
            lambda x: "🔴" * int(x - 6)  # Nombre d'icônes selon le score
        )
        
        st.dataframe(
            resistance_levels[['niveau', 'force']],
            use_container_width=True
        )
    
    # Alertes personnalisées
    st.markdown("### 🔔 Alertes Suggérées")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("""
        **Prix à surveiller:**
        - RSI > 70
        - Volume > 2x moyenne
        - Test résistance majeure
        """)
    
    with col2:
        st.info("""
        **Temps à surveiller:**
        - Heures: 12h-16h UTC
        - Jours: Mercredi-Jeudi
        - Cycles: ~90 jours
        """)


def export_scored_tops(scored_tops, tz_name):
    """Export des tops scorés"""
    
    st.subheader("📋 Export des Données")
    
    # Préparer les données pour export
    export_df = scored_tops.copy()
    export_df['timestamp'] = export_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Options d'export
    col1, col2 = st.columns(2)
    
    with col1:
        # CSV complet
        csv = export_df.to_csv(index=False)
        st.download_button(
            label="📥 Télécharger CSV Complet",
            data=csv,
            file_name=f"tops_scores_{tz_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    
    with col2:
        # Top scores uniquement
        top_scores = export_df[export_df['score'] >= 7]
        if not top_scores.empty:
            csv_top = top_scores.to_csv(index=False)
            st.download_button(
                label="🎯 Télécharger Tops Majeurs",
                data=csv_top,
                file_name=f"tops_majeurs_{tz_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
    
    # Résumé pour notes
    st.markdown("### 📝 Résumé pour Notes")
    
    summary = f"""
    # Analyse des Tops - {tz_name}
    Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
    
    ## Statistiques Générales
    - Total Tops Analysés: {len(scored_tops)}
    - Score Moyen: {scored_tops['score'].mean():.2f}/10
    - Tops Majeurs (≥8): {len(scored_tops[scored_tops['score'] >= 8])}
    - Tops Confirmés (≥7): {len(scored_tops[scored_tops['score'] >= 7])}
    
    ## Top 3 Meilleurs Scores
    """
    
    for i, top in scored_tops.head(3).iterrows():
        summary += f"""
    {i+1}. {top['timestamp'].strftime('%Y-%m-%d')} - Score: {top['score']:.2f}/10
       Prix: ${top['price']:,.0f} - {top['confidence']}
    """
    
    st.text_area("Résumé", summary, height=300)