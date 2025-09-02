"""
Système de Scoring Avancé pour les Tops - Version GPT-5
Basé sur les recommandations techniques avancées
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from scipy import stats
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

class GPT5TopScoringSystem:
    """
    Système de scoring avancé pour les tops basé sur les recommandations GPT-5
    Détection des excès haussiers et signaux de retournement
    """
    
    def __init__(self):
        self.score_weights = {
            'bollinger_excess': 3,      # Excès au-dessus de BB haute
            'volume_zscore': 3,          # Volume anormal
            'wick_top': 1,               # Mèche haute (prise de profits)
            'rsi_overbought': 1,         # RSI > 70
            'rsi_divergence': 2,         # Divergence baissière
            'local_high': 2,             # Plus haut local
            'psychological_level': 1,     # Niveau psychologique
            'derivatives': 1,            # Funding/premium (proxy)
        }
        self.max_score = 10
    
    def calculate_top_score_gpt5(self, idx, row, df, lookback_short=30, lookback_long=90):
        """
        Calcule le score d'un top selon la méthodologie GPT-5
        
        Args:
            idx: Index de la bougie à analyser
            row: Données de la bougie
            df: DataFrame complet
            lookback_short: Période courte pour plus haut local
            lookback_long: Période longue pour plus haut majeur
        
        Returns:
            dict avec score et détails
        """
        score_details = {}
        total_score = 0
        
        # 1. EXCÈS BOLLINGER (0-3 points)
        if 'bb_high' in row and 'bb_low' in row and pd.notna(row['bb_high']):
            band_width = row['bb_high'] - row['bb_low']
            if band_width > 0:
                band_z_top = (row['close'] - row['bb_high']) / band_width
                
                if band_z_top > 0.20:
                    score_details['bollinger_excess'] = 3
                    total_score += 3
                elif band_z_top > 0.10:
                    score_details['bollinger_excess'] = 2
                    total_score += 2
                elif band_z_top > 0:
                    score_details['bollinger_excess'] = 1
                    total_score += 1
                else:
                    score_details['bollinger_excess'] = 0
            else:
                score_details['bollinger_excess'] = 0
        
        # 2. VOLUME Z-SCORE (0-3 points)
        if 'volume' in row and pd.notna(row['volume']):
            # Calculer le z-score du volume
            idx_pos = df.index.get_loc(idx)
            if idx_pos >= 20:
                recent_volumes = df.iloc[max(0, idx_pos-20):idx_pos]['volume']
                if len(recent_volumes) > 0:
                    vol_mean = recent_volumes.mean()
                    vol_std = recent_volumes.std()
                    
                    if vol_std > 0:
                        vol_zscore = (row['volume'] - vol_mean) / vol_std
                        
                        if vol_zscore > 3:
                            score_details['volume_zscore'] = 3
                            total_score += 3
                        elif vol_zscore > 2:
                            score_details['volume_zscore'] = 2
                            total_score += 2
                        elif vol_zscore > 1:
                            score_details['volume_zscore'] = 1
                            total_score += 1
                        else:
                            score_details['volume_zscore'] = 0
                    else:
                        score_details['volume_zscore'] = 0
        
        # 3. WICK TOP RATIO (0-1 point)
        if all(k in row for k in ['high', 'open', 'close', 'low']):
            body = abs(row['close'] - row['open'])
            wick_top = row['high'] - max(row['open'], row['close'])
            
            if body > 0:
                wick_ratio_top = wick_top / body
                
                if wick_ratio_top >= 1.5:
                    score_details['wick_top'] = 1
                    total_score += 1
                else:
                    score_details['wick_top'] = 0
            else:
                score_details['wick_top'] = 0
        
        # 4. RSI OVERBOUGHT (0-1 point)
        if 'rsi' in row and pd.notna(row['rsi']):
            if row['rsi'] > 70:
                score_details['rsi_overbought'] = 1
                total_score += 1
            else:
                score_details['rsi_overbought'] = 0
        
        # 5. RSI DIVERGENCE BAISSIÈRE (0-2 points)
        divergence_score = self._check_bearish_divergence(idx, df)
        score_details['rsi_divergence'] = divergence_score
        total_score += divergence_score
        
        # 6. PLUS HAUT LOCAL (0-2 points)
        idx_pos = df.index.get_loc(idx)
        
        # Plus haut 30 périodes
        if idx_pos >= lookback_short:
            window_short = df.iloc[max(0, idx_pos-lookback_short):idx_pos+1]
            if row['high'] == window_short['high'].max():
                score_details['local_high'] = 1
                total_score += 1
                
                # Plus haut 90 périodes
                if idx_pos >= lookback_long:
                    window_long = df.iloc[max(0, idx_pos-lookback_long):idx_pos+1]
                    if row['high'] == window_long['high'].max():
                        score_details['local_high'] = 2
                        total_score += 1  # +1 additionnel
        else:
            score_details['local_high'] = 0
        
        # 7. NIVEAU PSYCHOLOGIQUE (0-1 point)
        psychological_levels = [
            100000, 110000, 112000, 115000, 120000,  # Bitcoin
            90000, 95000, 105000, 125000, 130000,
            150000, 200000
        ]
        
        price = row['high']
        for level in psychological_levels:
            if abs(price - level) / level < 0.01:  # Moins de 1% du niveau
                score_details['psychological_level'] = 1
                total_score += 1
                break
        else:
            score_details['psychological_level'] = 0
        
        # 8. PROXY DERIVATIVES (0-1 point)
        # Utiliser une poussée verticale comme proxy
        if idx_pos >= 5:
            recent_bars = df.iloc[max(0, idx_pos-5):idx_pos+1]
            consecutive_ups = 0
            
            for i in range(1, len(recent_bars)):
                if recent_bars.iloc[i]['close'] > recent_bars.iloc[i-1]['close']:
                    consecutive_ups += 1
            
            if consecutive_ups >= 4 and 'bb_width' in row:
                # Bandes qui s'écartent + poussée verticale
                if idx_pos >= 10:
                    prev_width = df.iloc[idx_pos-5]['bb_width'] if 'bb_width' in df.columns else 0
                    current_width = row['bb_width'] if 'bb_width' in row else 0
                    
                    if current_width > prev_width * 1.2:  # Élargissement de 20%
                        score_details['derivatives'] = 1
                        total_score += 1
                    else:
                        score_details['derivatives'] = 0
                else:
                    score_details['derivatives'] = 0
            else:
                score_details['derivatives'] = 0
        
        # Normaliser le score sur 10
        final_score = min(total_score, 10)
        
        # Déterminer la catégorie
        if final_score >= 8:
            category = "TOP_MAJEUR"
            confidence = "TRÈS_ÉLEVÉ"
        elif final_score >= 6:
            category = "TOP_SOLIDE"
            confidence = "ÉLEVÉ"
        elif final_score >= 4:
            category = "TOP_POSSIBLE"
            confidence = "MOYEN"
        else:
            category = "SIGNAL_FAIBLE"
            confidence = "FAIBLE"
        
        return {
            'score': final_score,
            'category': category,
            'confidence': confidence,
            'details': score_details,
            'band_z_top': band_z_top if 'band_z_top' in locals() else 0,
            'vol_zscore': vol_zscore if 'vol_zscore' in locals() else 0,
            'wick_ratio': wick_ratio_top if 'wick_ratio_top' in locals() else 0
        }
    
    def _check_bearish_divergence(self, idx, df, lookback=14):
        """
        Vérifie la divergence baissière RSI
        Prix fait un plus haut mais RSI fait un plus bas
        """
        if 'rsi' not in df.columns:
            return 0
        
        idx_pos = df.index.get_loc(idx)
        if idx_pos < lookback * 2:
            return 0
        
        # Trouver le précédent plus haut
        window = df.iloc[max(0, idx_pos-lookback*2):idx_pos]
        
        if len(window) < lookback:
            return 0
        
        # Identifier les sommets locaux
        highs = []
        for i in range(1, len(window)-1):
            if (window.iloc[i]['high'] > window.iloc[i-1]['high'] and 
                window.iloc[i]['high'] > window.iloc[i+1]['high']):
                highs.append(i)
        
        if len(highs) >= 1:
            # Comparer avec le dernier sommet
            last_high_idx = highs[-1]
            
            # Prix actuel > prix précédent sommet
            price_higher = df.iloc[idx_pos]['high'] > window.iloc[last_high_idx]['high']
            
            # RSI actuel < RSI précédent sommet
            rsi_lower = df.iloc[idx_pos]['rsi'] < window.iloc[last_high_idx]['rsi']
            
            if price_higher and rsi_lower:
                return 2  # Divergence confirmée
        
        return 0
    
    def check_confirmation(self, idx, df, n_bars=4, drop_threshold=0.05):
        """
        Vérifie la confirmation du top (sans look-ahead bias)
        
        Args:
            idx: Index du signal de top
            df: DataFrame
            n_bars: Nombre de bougies pour confirmation
            drop_threshold: Seuil de baisse pour confirmation
        
        Returns:
            dict avec statut de confirmation
        """
        idx_pos = df.index.get_loc(idx)
        
        if idx_pos >= len(df) - n_bars:
            return {'confirmed': False, 'reason': 'Pas assez de données futures'}
        
        signal_high = df.iloc[idx_pos]['high']
        signal_close = df.iloc[idx_pos]['close']
        
        # Vérifier les n bougies suivantes
        for i in range(1, n_bars + 1):
            future_idx = idx_pos + i
            if future_idx >= len(df):
                break
            
            future_bar = df.iloc[future_idx]
            
            # Confirmation 1: Clôture sous BB mid
            if 'bb_mid' in future_bar and pd.notna(future_bar['bb_mid']):
                if future_bar['close'] < future_bar['bb_mid']:
                    return {
                        'confirmed': True,
                        'reason': f'Clôture sous BB mid en {i} bougies',
                        'bars_to_confirm': i
                    }
            
            # Confirmation 2: Baisse de -X%
            drop_pct = (future_bar['close'] - signal_close) / signal_close
            if drop_pct <= -drop_threshold:
                return {
                    'confirmed': True,
                    'reason': f'Baisse de {drop_pct*100:.1f}% en {i} bougies',
                    'bars_to_confirm': i
                }
        
        return {'confirmed': False, 'reason': 'Pas de confirmation dans le délai'}
    
    def apply_anti_fake_filters(self, score_data, idx, df):
        """
        Applique des filtres anti-fake pour éviter les faux signaux
        
        Args:
            score_data: Données de score du top
            idx: Index du signal
            df: DataFrame
        
        Returns:
            dict avec score ajusté et raisons
        """
        adjustments = []
        original_score = score_data['score']
        adjusted_score = original_score
        
        idx_pos = df.index.get_loc(idx)
        
        # 1. Filtre Trend Fort (bandes qui s'élargissent rapidement)
        if idx_pos >= 10 and 'bb_high' in df.columns:
            current_width = df.iloc[idx_pos]['bb_high'] - df.iloc[idx_pos]['bb_low']
            prev_width = df.iloc[idx_pos-5]['bb_high'] - df.iloc[idx_pos-5]['bb_low']
            
            width_expansion = (current_width - prev_width) / prev_width if prev_width > 0 else 0
            
            if width_expansion > 0.3:  # Expansion de 30%
                # Bande haute monte fortement = trend fort
                bb_high_change = (df.iloc[idx_pos]['bb_high'] - df.iloc[idx_pos-5]['bb_high']) / df.iloc[idx_pos-5]['bb_high']
                
                if bb_high_change > 0.05:  # Monte de plus de 5%
                    adjusted_score -= 2
                    adjustments.append("Trend fort détecté (-2)")
        
        # 2. Filtre Weekend (liquidité faible)
        if hasattr(idx, 'weekday'):
            if idx.weekday() in [5, 6]:  # Samedi, Dimanche
                adjusted_score -= 1
                adjustments.append("Weekend - liquidité faible (-1)")
        
        # 3. Filtre Double Top (plus fiable)
        if idx_pos >= 20:
            recent_window = df.iloc[max(0, idx_pos-20):idx_pos]
            high_counts = (recent_window['high'] > recent_window['high'].quantile(0.95)).sum()
            
            if high_counts >= 2:
                adjusted_score += 1
                adjustments.append("Double top détecté (+1)")
        
        # 4. Filtre Volume Climax
        if 'vol_zscore' in score_data['details'] and score_data['details']['vol_zscore'] > 3:
            # Volume extrême = plus fiable
            adjusted_score += 1
            adjustments.append("Volume climax (+1)")
        
        # Limiter le score entre 0 et 10
        adjusted_score = max(0, min(10, adjusted_score))
        
        return {
            'original_score': original_score,
            'adjusted_score': adjusted_score,
            'adjustments': adjustments,
            'filter_impact': adjusted_score - original_score
        }
    
    def backtest_top_signals(self, df, min_score=6, tp_mode='bb_mid', stop_buffer=150):
        """
        Backtest des signaux de top avec entrée/sortie
        
        Args:
            df: DataFrame avec les données
            min_score: Score minimum pour considérer un top
            tp_mode: Mode de take profit ('bb_mid', 'bb_low', 'fixed_r')
            stop_buffer: Buffer au-dessus du high pour le stop
        
        Returns:
            DataFrame avec les résultats du backtest
        """
        trades = []
        
        for idx, row in df.iterrows():
            # Calculer le score
            score_data = self.calculate_top_score_gpt5(idx, row, df)
            
            if score_data['score'] >= min_score:
                # Vérifier la confirmation
                confirmation = self.check_confirmation(idx, df)
                
                if confirmation['confirmed']:
                    idx_pos = df.index.get_loc(idx)
                    entry_idx = idx_pos + confirmation['bars_to_confirm']
                    
                    if entry_idx < len(df):
                        entry_bar = df.iloc[entry_idx]
                        entry_price = entry_bar['close']
                        stop_loss = row['high'] + stop_buffer
                        
                        # Calculer le take profit selon le mode
                        if tp_mode == 'bb_mid':
                            take_profit = entry_bar['bb_mid'] if 'bb_mid' in entry_bar else entry_price * 0.95
                        elif tp_mode == 'bb_low':
                            take_profit = entry_bar['bb_low'] if 'bb_low' in entry_bar else entry_price * 0.90
                        else:  # fixed_r
                            risk = stop_loss - entry_price
                            take_profit = entry_price - (risk * 3)  # 3R par défaut
                        
                        # Simuler le trade
                        trade_result = self._simulate_short_trade(
                            entry_idx, entry_price, stop_loss, take_profit, df
                        )
                        
                        trade_result.update({
                            'signal_time': idx,
                            'score': score_data['score'],
                            'category': score_data['category']
                        })
                        
                        trades.append(trade_result)
        
        return pd.DataFrame(trades)
    
    def _simulate_short_trade(self, entry_idx, entry_price, stop_loss, take_profit, df):
        """
        Simule un trade short avec stop loss et take profit
        """
        for i in range(entry_idx + 1, min(entry_idx + 100, len(df))):
            bar = df.iloc[i]
            
            # Check stop loss (perte)
            if bar['high'] >= stop_loss:
                return {
                    'exit_idx': i,
                    'exit_price': stop_loss,
                    'pnl': (entry_price - stop_loss) / entry_price,  # Négatif car on perd
                    'result': 'STOP_LOSS',
                    'bars_held': i - entry_idx
                }
            
            # Check take profit (gain)
            if bar['low'] <= take_profit:
                return {
                    'exit_idx': i,
                    'exit_price': take_profit,
                    'pnl': (entry_price - take_profit) / entry_price,  # Positif car on gagne
                    'result': 'TAKE_PROFIT',
                    'bars_held': i - entry_idx
                }
        
        # Ni SL ni TP atteint
        final_price = df.iloc[-1]['close']
        return {
            'exit_idx': len(df) - 1,
            'exit_price': final_price,
            'pnl': (entry_price - final_price) / entry_price,
            'result': 'TIME_OUT',
            'bars_held': len(df) - 1 - entry_idx
        }


def create_gpt5_tops_scoring_interface(df, tops, selected_tz_name):
    """
    Interface Streamlit pour le système de scoring GPT-5
    """
    st.header(f"🎯 Système de Scoring GPT-5 pour les Tops - {selected_tz_name}")
    
    st.info("""
    **Système basé sur les recommandations GPT-5:**
    - Excès Bollinger + Volume Z-score
    - Détection des divergences RSI
    - Confirmation sans look-ahead bias
    - Filtres anti-fake (trend fort, weekend)
    - Backtest avec entrée/sortie réaliste
    """)
    
    # Initialiser le système
    scoring_system = GPT5TopScoringSystem()
    
    # Calculer les scores pour tous les tops
    if not tops.empty and not df.empty:
        # Ajouter les indicateurs nécessaires si manquants
        df = add_required_indicators(df)
        
        # Sous-onglets
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Scoring Live",
            "✅ Confirmation",
            "🛡️ Filtres Anti-Fake",
            "📈 Backtest",
            "📋 Export Détaillé"
        ])
        
        with tab1:
            display_live_scoring(df, tops, scoring_system, selected_tz_name)
        
        with tab2:
            display_confirmation_analysis(df, tops, scoring_system, selected_tz_name)
        
        with tab3:
            display_anti_fake_filters(df, tops, scoring_system, selected_tz_name)
        
        with tab4:
            display_backtest_results(df, scoring_system, selected_tz_name)
        
        with tab5:
            export_gpt5_analysis(df, tops, scoring_system, selected_tz_name)
    
    else:
        st.warning("Aucune donnée disponible pour l'analyse")


def add_required_indicators(df):
    """Ajoute les indicateurs requis pour le scoring GPT-5"""
    
    # Bollinger Bands
    if 'bb_high' not in df.columns:
        bb = BollingerBands(close=df['close'], window=20, window_dev=2)
        df['bb_high'] = bb.bollinger_hband()
        df['bb_mid'] = bb.bollinger_mavg()
        df['bb_low'] = bb.bollinger_lband()
        df['bb_width'] = df['bb_high'] - df['bb_low']
    
    # RSI
    if 'rsi' not in df.columns:
        rsi = RSIIndicator(close=df['close'], window=14)
        df['rsi'] = rsi.rsi()
    
    return df


def display_live_scoring(df, tops, scoring_system, tz_name):
    """Affiche le scoring en temps réel"""
    
    st.subheader("📊 Analyse Live des Tops")
    
    # Sélection de la période
    col1, col2 = st.columns(2)
    
    with col1:
        lookback = st.slider("Nombre de tops à analyser", 10, 100, 50)
    
    with col2:
        min_score = st.slider("Score minimum", 0, 10, 6)
    
    # Analyser les derniers tops
    recent_tops = tops.sort_index(ascending=False).head(lookback)
    
    scored_tops = []
    for idx, top in recent_tops.iterrows():
        # Trouver la position dans df
        if idx in df.index:
            score_data = scoring_system.calculate_top_score_gpt5(idx, df.loc[idx], df)
            
            scored_tops.append({
                'Date': idx.strftime('%Y-%m-%d %H:%M'),
                'Prix': f"${top['price']:,.0f}",
                'Score': score_data['score'],
                'Catégorie': score_data['category'],
                'Confiance': score_data['confidence'],
                'Band Z': f"{score_data['band_z_top']:.3f}",
                'Vol Z': f"{score_data['vol_zscore']:.2f}",
                'Wick': f"{score_data['wick_ratio']:.2f}"
            })
    
    # Filtrer par score minimum
    scored_df = pd.DataFrame(scored_tops)
    if not scored_df.empty:
        filtered_df = scored_df[scored_df['Score'] >= min_score]
        
        # Afficher les statistiques
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Tops Majeurs (≥8)", len(scored_df[scored_df['Score'] >= 8]))
        with col2:
            st.metric("Tops Solides (≥6)", len(scored_df[scored_df['Score'] >= 6]))
        with col3:
            avg_score = scored_df['Score'].mean()
            st.metric("Score Moyen", f"{avg_score:.2f}")
        with col4:
            max_score = scored_df['Score'].max()
            st.metric("Score Max", f"{max_score}")
        
        # Tableau des résultats
        st.dataframe(
            filtered_df,
            use_container_width=True,
            height=400
        )
        
        # Graphique des scores
        fig = px.bar(
            scored_df.head(20),
            x='Date',
            y='Score',
            color='Score',
            color_continuous_scale='RdYlGn_r',
            title="Scores des 20 Derniers Tops"
        )
        
        fig.add_hline(y=8, line_dash="dash", line_color="red", 
                      annotation_text="Top Majeur")
        fig.add_hline(y=6, line_dash="dash", line_color="orange",
                      annotation_text="Top Solide")
        
        st.plotly_chart(fig, use_container_width=True)


def display_confirmation_analysis(df, tops, scoring_system, tz_name):
    """Analyse de la confirmation des tops"""
    
    st.subheader("✅ Analyse de Confirmation")
    
    col1, col2 = st.columns(2)
    
    with col1:
        n_bars = st.slider("Bougies pour confirmation", 1, 10, 4)
    
    with col2:
        drop_threshold = st.slider("Seuil de baisse (%)", 1, 10, 5) / 100
    
    # Analyser les confirmations
    confirmations = []
    
    for idx, top in tops.head(30).iterrows():
        if idx in df.index:
            score_data = scoring_system.calculate_top_score_gpt5(idx, df.loc[idx], df)
            
            if score_data['score'] >= 6:
                confirmation = scoring_system.check_confirmation(idx, df, n_bars, drop_threshold)
                
                confirmations.append({
                    'Date': idx.strftime('%Y-%m-%d %H:%M'),
                    'Score': score_data['score'],
                    'Confirmé': '✅' if confirmation['confirmed'] else '❌',
                    'Raison': confirmation['reason'],
                    'Bougies': confirmation.get('bars_to_confirm', 'N/A')
                })
    
    if confirmations:
        conf_df = pd.DataFrame(confirmations)
        
        # Statistiques
        confirmed_count = len(conf_df[conf_df['Confirmé'] == '✅'])
        total_count = len(conf_df)
        
        st.metric("Taux de Confirmation", 
                  f"{confirmed_count}/{total_count} ({confirmed_count/total_count*100:.1f}%)")
        
        # Tableau
        st.dataframe(conf_df, use_container_width=True)
        
        # Analyse par score
        st.subheader("📊 Confirmation par Niveau de Score")
        
        for score_level in [8, 7, 6]:
            level_df = conf_df[conf_df['Score'] >= score_level]
            if not level_df.empty:
                confirmed = len(level_df[level_df['Confirmé'] == '✅'])
                total = len(level_df)
                st.write(f"**Score ≥ {score_level}**: {confirmed}/{total} confirmés ({confirmed/total*100:.1f}%)")


def display_anti_fake_filters(df, tops, scoring_system, tz_name):
    """Affiche l'impact des filtres anti-fake"""
    
    st.subheader("🛡️ Filtres Anti-Fake")
    
    st.info("""
    **Filtres appliqués:**
    - Trend fort (bandes en expansion) : -2 points
    - Weekend (liquidité faible) : -1 point
    - Double top détecté : +1 point
    - Volume climax : +1 point
    """)
    
    # Analyser avec et sans filtres
    filtered_results = []
    
    for idx, top in tops.head(20).iterrows():
        if idx in df.index:
            score_data = scoring_system.calculate_top_score_gpt5(idx, df.loc[idx], df)
            filter_result = scoring_system.apply_anti_fake_filters(score_data, idx, df)
            
            filtered_results.append({
                'Date': idx.strftime('%Y-%m-%d %H:%M'),
                'Score Original': filter_result['original_score'],
                'Score Ajusté': filter_result['adjusted_score'],
                'Impact': filter_result['filter_impact'],
                'Ajustements': ', '.join(filter_result['adjustments']) if filter_result['adjustments'] else 'Aucun'
            })
    
    if filtered_results:
        filter_df = pd.DataFrame(filtered_results)
        
        # Statistiques
        col1, col2, col3 = st.columns(3)
        
        with col1:
            avg_impact = filter_df['Impact'].mean()
            st.metric("Impact Moyen", f"{avg_impact:+.2f}")
        
        with col2:
            filtered_count = len(filter_df[filter_df['Impact'] != 0])
            st.metric("Tops Filtrés", f"{filtered_count}/{len(filter_df)}")
        
        with col3:
            major_changes = len(filter_df[abs(filter_df['Impact']) >= 2])
            st.metric("Changements Majeurs", major_changes)
        
        # Tableau
        st.dataframe(filter_df, use_container_width=True)
        
        # Graphique avant/après
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=filter_df['Date'],
            y=filter_df['Score Original'],
            name='Score Original',
            marker_color='lightblue'
        ))
        
        fig.add_trace(go.Bar(
            x=filter_df['Date'],
            y=filter_df['Score Ajusté'],
            name='Score Ajusté',
            marker_color='darkblue'
        ))
        
        fig.update_layout(
            title="Impact des Filtres Anti-Fake",
            barmode='group',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)


def display_backtest_results(df, scoring_system, tz_name):
    """Affiche les résultats du backtest"""
    
    st.subheader("📈 Backtest des Signaux de Top")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        min_score = st.slider("Score minimum pour trade", 4, 9, 6)
    
    with col2:
        tp_mode = st.selectbox("Mode Take Profit", 
                               ['bb_mid', 'bb_low', 'fixed_r'])
    
    with col3:
        stop_buffer = st.number_input("Buffer Stop Loss (points)", 
                                      50, 500, 150, step=50)
    
    if st.button("🚀 Lancer Backtest"):
        with st.spinner("Backtest en cours..."):
            results = scoring_system.backtest_top_signals(
                df, min_score, tp_mode, stop_buffer
            )
            
            if not results.empty:
                # Statistiques
                winning_trades = results[results['pnl'] > 0]
                losing_trades = results[results['pnl'] < 0]
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Trades", len(results))
                
                with col2:
                    win_rate = len(winning_trades) / len(results) * 100
                    st.metric("Win Rate", f"{win_rate:.1f}%")
                
                with col3:
                    avg_pnl = results['pnl'].mean() * 100
                    st.metric("PnL Moyen", f"{avg_pnl:.2f}%")
                
                with col4:
                    sharpe = results['pnl'].mean() / results['pnl'].std() if results['pnl'].std() > 0 else 0
                    st.metric("Sharpe Ratio", f"{sharpe:.2f}")
                
                # Distribution des résultats
                st.subheader("📊 Distribution des Résultats")
                
                fig = px.histogram(
                    results,
                    x='pnl',
                    nbins=20,
                    title="Distribution des PnL",
                    labels={'pnl': 'PnL (%)', 'count': 'Nombre de trades'}
                )
                
                fig.add_vline(x=0, line_dash="dash", line_color="red")
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Détail des trades
                st.subheader("📋 Détail des Trades")
                
                display_results = results.copy()
                display_results['signal_time'] = display_results['signal_time'].dt.strftime('%Y-%m-%d %H:%M')
                display_results['pnl'] = (display_results['pnl'] * 100).apply(lambda x: f"{x:.2f}%")
                
                st.dataframe(
                    display_results[['signal_time', 'score', 'category', 'result', 'pnl', 'bars_held']],
                    use_container_width=True
                )
            else:
                st.warning("Aucun signal de trade trouvé avec ces paramètres")


def export_gpt5_analysis(df, tops, scoring_system, tz_name):
    """Export de l'analyse GPT-5"""
    
    st.subheader("📋 Export de l'Analyse GPT-5")
    
    # Préparer les données complètes
    export_data = []
    
    for idx, top in tops.iterrows():
        if idx in df.index:
            score_data = scoring_system.calculate_top_score_gpt5(idx, df.loc[idx], df)
            confirmation = scoring_system.check_confirmation(idx, df)
            filter_result = scoring_system.apply_anti_fake_filters(score_data, idx, df)
            
            export_data.append({
                'timestamp': idx,
                'price': top['price'],
                'score_original': score_data['score'],
                'score_adjusted': filter_result['adjusted_score'],
                'category': score_data['category'],
                'confidence': score_data['confidence'],
                'confirmed': confirmation['confirmed'],
                'band_z_top': score_data['band_z_top'],
                'vol_zscore': score_data['vol_zscore'],
                'details': str(score_data['details'])
            })
    
    if export_data:
        export_df = pd.DataFrame(export_data)
        
        # CSV
        csv = export_df.to_csv(index=False)
        st.download_button(
            label="📥 Télécharger Analyse Complète (CSV)",
            data=csv,
            file_name=f"gpt5_tops_analysis_{tz_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
        
        # Résumé
        st.markdown("### 📝 Résumé de l'Analyse")
        
        summary = f"""
        # Analyse GPT-5 des Tops - {tz_name}
        Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        
        ## Statistiques
        - Total Tops Analysés: {len(export_df)}
        - Score Moyen: {export_df['score_original'].mean():.2f}
        - Tops Majeurs (≥8): {len(export_df[export_df['score_original'] >= 8])}
        - Taux de Confirmation: {export_df['confirmed'].sum() / len(export_df) * 100:.1f}%
        
        ## Recommandations
        - Utiliser score ≥6 pour signaux fiables
        - Attendre confirmation avant d'entrer
        - Appliquer filtres anti-fake en trend fort
        """
        
        st.text_area("Résumé", summary, height=300)