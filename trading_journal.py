"""
Journal de Trading Professionnel
Système complet de logging et analyse des trades
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import json
import os
from PIL import Image
import io
import base64
import uuid

class TradingJournal:
    """
    Système de journal de trading professionnel
    """
    
    def __init__(self, data_path="data/trading_journal.csv"):
        self.data_path = data_path
        self.ensure_data_directory()
        self.trades_df = self.load_trades()
    
    def ensure_data_directory(self):
        """Crée le répertoire data s'il n'existe pas"""
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
    
    def load_trades(self):
        """Charge les trades existants ou crée un DataFrame vide"""
        try:
            df = pd.read_csv(self.data_path)
            df['datetime'] = pd.to_datetime(df['datetime'])
            # Ajouter les colonnes manquantes si nécessaire
            if 'id' not in df.columns:
                df['id'] = [str(uuid.uuid4()) for _ in range(len(df))]
            if 'type' not in df.columns:
                df['type'] = 'Trade'
            if 'is_deleted' not in df.columns:
                df['is_deleted'] = False
            return df
        except:
            return pd.DataFrame(columns=[
                'id', 'datetime', 'type', 'setup_type', 'score_signal', 'direction',
                'entry_price', 'stop_loss', 'take_profit', 'position_size',
                'rr_planned', 'rr_realized', 'pnl_dollars', 'pnl_percent',
                'confidence', 'status', 'exit_price', 'exit_datetime',
                'max_drawdown', 'max_profit', 'duration_hours',
                'market_context', 'notes', 'screenshot_path',
                'indicators', 'mistakes', 'lessons', 'is_deleted'
            ])
    
    def save_trades(self):
        """Sauvegarde les trades dans le CSV"""
        self.trades_df.to_csv(self.data_path, index=False)
    
    def add_trade(self, trade_data):
        """Ajoute un nouveau trade au journal"""
        # Ajouter un ID unique si pas présent
        if 'id' not in trade_data:
            trade_data['id'] = str(uuid.uuid4())
        
        # Type par défaut
        if 'type' not in trade_data:
            trade_data['type'] = 'Trade'
        
        # is_deleted par défaut
        if 'is_deleted' not in trade_data:
            trade_data['is_deleted'] = False
        
        # Calculer automatiquement certains champs
        if trade_data['type'] == 'Trade' and trade_data.get('direction'):
            if trade_data['direction'] == 'Long':
                trade_data['rr_planned'] = (trade_data['take_profit'] - trade_data['entry_price']) / \
                                           (trade_data['entry_price'] - trade_data['stop_loss'])
            else:  # Short
                trade_data['rr_planned'] = (trade_data['entry_price'] - trade_data['take_profit']) / \
                                           (trade_data['stop_loss'] - trade_data['entry_price'])
        
        # Ajouter au DataFrame
        self.trades_df = pd.concat([self.trades_df, pd.DataFrame([trade_data])], ignore_index=True)
        self.save_trades()
        
        return True
    
    def add_no_trade_day(self, no_trade_data):
        """Ajoute un jour sans trade au journal"""
        no_trade_data['id'] = str(uuid.uuid4())
        no_trade_data['type'] = 'NoTrade'
        no_trade_data['is_deleted'] = False
        no_trade_data['status'] = 'NoTrade'
        
        # Mettre les champs non applicables à None ou 0
        for field in ['direction', 'entry_price', 'stop_loss', 'take_profit', 
                      'rr_planned', 'rr_realized', 'exit_price']:
            no_trade_data[field] = None
        
        no_trade_data['pnl_dollars'] = 0
        no_trade_data['pnl_percent'] = 0
        
        self.trades_df = pd.concat([self.trades_df, pd.DataFrame([no_trade_data])], ignore_index=True)
        self.save_trades()
        return True
    
    def delete_trade(self, trade_id, permanent=False):
        """Supprime ou archive un trade"""
        if permanent:
            # Suppression définitive
            self.trades_df = self.trades_df[self.trades_df['id'] != trade_id]
        else:
            # Archivage (soft delete)
            self.trades_df.loc[self.trades_df['id'] == trade_id, 'is_deleted'] = True
        
        self.save_trades()
        return True
    
    def get_active_trades(self):
        """Retourne uniquement les trades actifs (non supprimés)"""
        return self.trades_df[self.trades_df['is_deleted'] == False].copy()
    
    def restore_trade(self, trade_id):
        """Restaure un trade archivé"""
        self.trades_df.loc[self.trades_df['id'] == trade_id, 'is_deleted'] = False
        self.save_trades()
        return True
    
    def update_trade(self, trade_id, update_data):
        """Met à jour un trade existant (sortie, etc.)"""
        if trade_id < len(self.trades_df):
            for key, value in update_data.items():
                self.trades_df.loc[trade_id, key] = value
            
            # Calculer le RR réalisé
            trade = self.trades_df.loc[trade_id]
            if trade['direction'] == 'Long':
                self.trades_df.loc[trade_id, 'rr_realized'] = \
                    (update_data['exit_price'] - trade['entry_price']) / \
                    (trade['entry_price'] - trade['stop_loss'])
            else:
                self.trades_df.loc[trade_id, 'rr_realized'] = \
                    (trade['entry_price'] - update_data['exit_price']) / \
                    (trade['stop_loss'] - trade['entry_price'])
            
            # Calculer le PnL
            if trade['direction'] == 'Long':
                pnl_percent = (update_data['exit_price'] - trade['entry_price']) / trade['entry_price']
            else:
                pnl_percent = (trade['entry_price'] - update_data['exit_price']) / trade['entry_price']
            
            self.trades_df.loc[trade_id, 'pnl_percent'] = pnl_percent * 100
            self.trades_df.loc[trade_id, 'pnl_dollars'] = pnl_percent * trade['position_size']
            
            # Calculer la durée
            if 'exit_datetime' in update_data:
                duration = pd.to_datetime(update_data['exit_datetime']) - trade['datetime']
                self.trades_df.loc[trade_id, 'duration_hours'] = duration.total_seconds() / 3600
            
            self.save_trades()
            return True
        return False
    
    def get_statistics(self):
        """Calcule les statistiques globales"""
        if self.trades_df.empty:
            return {}
        
        closed_trades = self.trades_df[self.trades_df['status'] == 'Closed']
        
        if closed_trades.empty:
            return {
                'total_trades': len(self.trades_df),
                'open_trades': len(self.trades_df),
                'closed_trades': 0
            }
        
        winning_trades = closed_trades[closed_trades['pnl_dollars'] > 0]
        losing_trades = closed_trades[closed_trades['pnl_dollars'] < 0]
        
        stats = {
            'total_trades': len(self.trades_df),
            'open_trades': len(self.trades_df[self.trades_df['status'] == 'Open']),
            'closed_trades': len(closed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(closed_trades) * 100 if len(closed_trades) > 0 else 0,
            'total_pnl': closed_trades['pnl_dollars'].sum(),
            'avg_win': winning_trades['pnl_dollars'].mean() if not winning_trades.empty else 0,
            'avg_loss': losing_trades['pnl_dollars'].mean() if not losing_trades.empty else 0,
            'largest_win': winning_trades['pnl_dollars'].max() if not winning_trades.empty else 0,
            'largest_loss': losing_trades['pnl_dollars'].min() if not losing_trades.empty else 0,
            'avg_rr_planned': closed_trades['rr_planned'].mean() if 'rr_planned' in closed_trades else 0,
            'avg_rr_realized': closed_trades['rr_realized'].mean() if 'rr_realized' in closed_trades else 0,
            'profit_factor': abs(winning_trades['pnl_dollars'].sum() / losing_trades['pnl_dollars'].sum()) 
                            if not losing_trades.empty and losing_trades['pnl_dollars'].sum() != 0 else 0,
            'sharpe_ratio': closed_trades['pnl_percent'].mean() / closed_trades['pnl_percent'].std() 
                           if closed_trades['pnl_percent'].std() != 0 else 0,
            'avg_duration': closed_trades['duration_hours'].mean() if 'duration_hours' in closed_trades else 0
        }
        
        # Statistiques par setup
        stats['by_setup'] = {}
        for setup in closed_trades['setup_type'].unique():
            setup_trades = closed_trades[closed_trades['setup_type'] == setup]
            setup_wins = setup_trades[setup_trades['pnl_dollars'] > 0]
            
            stats['by_setup'][setup] = {
                'count': len(setup_trades),
                'win_rate': len(setup_wins) / len(setup_trades) * 100,
                'avg_pnl': setup_trades['pnl_dollars'].mean(),
                'total_pnl': setup_trades['pnl_dollars'].sum()
            }
        
        return stats
    
    def calculate_equity_curve(self):
        """Calcule la courbe d'équité"""
        if self.trades_df.empty:
            return pd.DataFrame()
        
        closed_trades = self.trades_df[self.trades_df['status'] == 'Closed'].copy()
        
        if closed_trades.empty:
            return pd.DataFrame()
        
        closed_trades = closed_trades.sort_values('datetime')
        closed_trades['cumulative_pnl'] = closed_trades['pnl_dollars'].cumsum()
        
        return closed_trades[['datetime', 'cumulative_pnl', 'pnl_dollars']]
    
    def get_drawdown_analysis(self):
        """Analyse les drawdowns"""
        equity_curve = self.calculate_equity_curve()
        
        if equity_curve.empty:
            return {}
        
        # Calculer le drawdown
        cumsum = equity_curve['cumulative_pnl']
        running_max = cumsum.expanding().max()
        drawdown = cumsum - running_max
        
        return {
            'current_drawdown': drawdown.iloc[-1] if not drawdown.empty else 0,
            'max_drawdown': drawdown.min(),
            'max_drawdown_date': equity_curve.loc[drawdown.idxmin(), 'datetime'] if not drawdown.empty else None,
            'recovery_time': self._calculate_recovery_time(drawdown, equity_curve)
        }
    
    def _calculate_recovery_time(self, drawdown, equity_curve):
        """Calcule le temps de récupération moyen après drawdown"""
        # Simplified calculation
        if drawdown.min() >= 0:
            return 0
        
        # Find periods of drawdown
        in_drawdown = drawdown < 0
        # Calculate average duration of drawdown periods
        # This is simplified - a more complex implementation would track each drawdown period
        return "À implémenter"


def create_trading_journal_interface(selected_tz_name):
    """
    Interface Streamlit pour le journal de trading
    """
    st.header(f"📓 Journal de Trading Professionnel - {selected_tz_name}")
    
    # Initialiser le journal
    journal = TradingJournal()
    
    # Tabs pour les différentes fonctionnalités
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📝 Nouveau Trade",
        "🗓️ Jour Sans Trade",
        "📊 Trades Actifs",
        "📈 Historique",
        "📊 Statistiques",
        "💹 Performance",
        "📋 Export/Import",
        "🗑️ Gérer Trades"
    ])
    
    with tab1:
        display_new_trade_form(journal, selected_tz_name)
    
    with tab2:
        display_no_trade_form(journal, selected_tz_name)
    
    with tab3:
        display_active_trades(journal, selected_tz_name)
    
    with tab4:
        display_trade_history(journal, selected_tz_name)
    
    with tab5:
        display_statistics(journal)
    
    with tab6:
        display_performance_analysis(journal)
    
    with tab7:
        display_export_import(journal)
    
    with tab8:
        display_trade_management(journal)


def display_new_trade_form(journal, tz_name):
    """Formulaire pour ajouter un nouveau trade"""
    
    st.subheader("📝 Enregistrer un Nouveau Trade")
    
    with st.form("new_trade_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            date_input = st.date_input(
                "Date d'entrée",
                value=datetime.now().date(),
                help="Date de l'entrée en position"
            )
            
            time_input = st.time_input(
                "Heure d'entrée",
                value=datetime.now().time(),
                help="Heure exacte de l'entrée"
            )
            
            # Combiner date et heure
            datetime_input = datetime.combine(date_input, time_input)
            
            setup_type = st.selectbox(
                "Type de Setup",
                ["Bottom 4H", "Top 4H", "Bottom 1H", "Top 1H", 
                 "Bottom Daily", "Top Daily", "Scalp", "Swing", "Autre"],
                help="Configuration qui a déclenché le trade"
            )
            
            direction = st.radio(
                "Direction",
                ["Long", "Short"],
                horizontal=True
            )
            
            score_signal = st.slider(
                "Score du Signal (0-10)",
                min_value=0.0,
                max_value=10.0,
                value=5.0,
                step=0.5,
                help="Score calculé par le système ou estimation manuelle"
            )
        
        with col2:
            entry_price = st.number_input(
                "Prix d'Entrée",
                min_value=0.0,
                value=100000.0,
                step=100.0,
                help="Prix exact d'exécution"
            )
            
            stop_loss = st.number_input(
                "Stop Loss",
                min_value=0.0,
                value=95000.0 if direction == "Long" else 105000.0,
                step=100.0,
                help="Niveau de stop loss"
            )
            
            take_profit = st.number_input(
                "Take Profit",
                min_value=0.0,
                value=110000.0 if direction == "Long" else 90000.0,
                step=100.0,
                help="Objectif de profit"
            )
            
            position_size = st.number_input(
                "Taille Position ($)",
                min_value=0.0,
                value=1000.0,
                step=100.0,
                help="Montant investi"
            )
        
        with col3:
            confidence = st.slider(
                "Niveau de Confiance",
                min_value=1,
                max_value=5,
                value=3,
                help="1=Très faible, 5=Très élevé"
            )
            
            market_context = st.selectbox(
                "Contexte de Marché",
                ["Bull Market", "Bear Market", "Range", "Breakout", 
                 "Consolidation", "High Volatility", "Low Volatility"],
                help="Conditions générales du marché"
            )
            
            # Indicateurs techniques au moment du trade
            st.markdown("**Indicateurs au moment du trade:**")
            rsi_value = st.number_input("RSI", min_value=0, max_value=100, value=50)
            volume_ratio = st.number_input("Volume Ratio", min_value=0.0, value=1.0, step=0.1)
        
        # Zone de texte pour les notes
        notes = st.text_area(
            "Notes et Analyse",
            height=100,
            placeholder="Raisons d'entrée, contexte, news, sentiment...",
            help="Documentez votre raisonnement"
        )
        
        # Upload screenshot
        screenshot = st.file_uploader(
            "Screenshot du Setup (optionnel)",
            type=['png', 'jpg', 'jpeg'],
            help="Capture d'écran du graphique"
        )
        
        # Boutons
        col1, col2 = st.columns(2)
        
        with col1:
            submitted = st.form_submit_button(
                "💾 Enregistrer le Trade",
                use_container_width=True,
                type="primary"
            )
        
        with col2:
            # Calcul automatique du RR
            if entry_price and stop_loss and take_profit:
                if direction == "Long":
                    rr = (take_profit - entry_price) / (entry_price - stop_loss) if entry_price > stop_loss else 0
                else:
                    rr = (entry_price - take_profit) / (stop_loss - entry_price) if stop_loss > entry_price else 0
                
                st.metric("R:R Prévu", f"{rr:.2f}")
        
        if submitted:
            # Préparer les données du trade
            trade_data = {
                'datetime': datetime_input,
                'setup_type': setup_type,
                'score_signal': score_signal,
                'direction': direction,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'position_size': position_size,
                'confidence': confidence,
                'status': 'Open',
                'market_context': market_context,
                'notes': notes,
                'indicators': json.dumps({
                    'rsi': rsi_value,
                    'volume_ratio': volume_ratio
                })
            }
            
            # Gérer le screenshot si fourni
            if screenshot:
                # Sauvegarder le screenshot
                screenshot_path = f"data/screenshots/{datetime_input.strftime('%Y%m%d_%H%M%S')}.png"
                os.makedirs("data/screenshots", exist_ok=True)
                
                with open(screenshot_path, "wb") as f:
                    f.write(screenshot.getbuffer())
                
                trade_data['screenshot_path'] = screenshot_path
            
            # Ajouter le trade
            if journal.add_trade(trade_data):
                st.success("✅ Trade enregistré avec succès!")
                st.balloons()
            else:
                st.error("❌ Erreur lors de l'enregistrement")


def display_active_trades(journal, tz_name):
    """Affiche et permet de gérer les trades actifs"""
    
    st.subheader("📊 Trades Actuellement Ouverts")
    
    active_trades = journal.trades_df[journal.trades_df['status'] == 'Open']
    
    if active_trades.empty:
        st.info("Aucun trade actif actuellement")
        return
    
    # Afficher les trades actifs
    for idx, trade in active_trades.iterrows():
        with st.expander(f"{trade['setup_type']} - {trade['direction']} @ ${trade['entry_price']:,.0f}"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**Date d'entrée:** {trade['datetime'].strftime('%Y-%m-%d %H:%M')}")
                st.write(f"**Score Signal:** {trade['score_signal']}/10")
                st.write(f"**Confiance:** {'⭐' * int(trade['confidence'])}")
            
            with col2:
                st.write(f"**Stop Loss:** ${trade['stop_loss']:,.0f}")
                st.write(f"**Take Profit:** ${trade['take_profit']:,.0f}")
                st.write(f"**R:R Prévu:** {trade['rr_planned']:.2f}")
            
            with col3:
                st.write(f"**Position:** ${trade['position_size']:,.0f}")
                st.write(f"**Contexte:** {trade['market_context']}")
            
            # Section pour clôturer le trade
            st.markdown("---")
            st.markdown("**🔒 Clôturer le Trade**")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                exit_price = st.number_input(
                    "Prix de Sortie",
                    min_value=0.0,
                    value=trade['entry_price'],
                    step=100.0,
                    key=f"exit_{idx}"
                )
            
            with col2:
                exit_date = st.date_input(
                    "Date de Sortie",
                    value=datetime.now().date(),
                    key=f"exit_date_{idx}"
                )
                
                exit_time = st.time_input(
                    "Heure de Sortie",
                    value=datetime.now().time(),
                    key=f"exit_time_{idx}"
                )
                
                exit_datetime = datetime.combine(exit_date, exit_time)
            
            with col3:
                # Afficher le PnL potentiel
                if trade['direction'] == 'Long':
                    pnl = (exit_price - trade['entry_price']) / trade['entry_price'] * 100
                else:
                    pnl = (trade['entry_price'] - exit_price) / trade['entry_price'] * 100
                
                color = "green" if pnl > 0 else "red"
                st.markdown(f"**PnL:** <span style='color:{color}'>{pnl:+.2f}%</span>", 
                           unsafe_allow_html=True)
            
            # Zone pour les leçons apprises
            col1, col2 = st.columns(2)
            
            with col1:
                mistakes = st.text_area(
                    "Erreurs commises",
                    key=f"mistakes_{idx}",
                    height=100
                )
            
            with col2:
                lessons = st.text_area(
                    "Leçons apprises",
                    key=f"lessons_{idx}",
                    height=100
                )
            
            if st.button(f"Clôturer Trade #{idx}", key=f"close_{idx}", type="primary"):
                update_data = {
                    'status': 'Closed',
                    'exit_price': exit_price,
                    'exit_datetime': exit_datetime,
                    'mistakes': mistakes,
                    'lessons': lessons
                }
                
                if journal.update_trade(idx, update_data):
                    st.success("Trade clôturé avec succès!")
                    st.rerun()


def display_trade_history(journal, tz_name):
    """Affiche l'historique complet des trades"""
    
    st.subheader("📈 Historique des Trades")
    
    if journal.trades_df.empty:
        st.info("Aucun trade enregistré")
        return
    
    # Filtres
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        filter_status = st.selectbox(
            "Statut",
            ["Tous", "Open", "Closed"]
        )
    
    with col2:
        filter_setup = st.selectbox(
            "Setup",
            ["Tous"] + list(journal.trades_df['setup_type'].unique())
        )
    
    with col3:
        filter_direction = st.selectbox(
            "Direction",
            ["Tous", "Long", "Short"]
        )
    
    with col4:
        filter_result = st.selectbox(
            "Résultat",
            ["Tous", "Gagnants", "Perdants"]
        )
    
    # Appliquer les filtres
    filtered_df = journal.trades_df.copy()
    
    if filter_status != "Tous":
        filtered_df = filtered_df[filtered_df['status'] == filter_status]
    
    if filter_setup != "Tous":
        filtered_df = filtered_df[filtered_df['setup_type'] == filter_setup]
    
    if filter_direction != "Tous":
        filtered_df = filtered_df[filtered_df['direction'] == filter_direction]
    
    if filter_result == "Gagnants":
        filtered_df = filtered_df[filtered_df['pnl_dollars'] > 0]
    elif filter_result == "Perdants":
        filtered_df = filtered_df[filtered_df['pnl_dollars'] < 0]
    
    # Afficher le tableau
    if not filtered_df.empty:
        # Préparer l'affichage
        display_df = filtered_df[['datetime', 'setup_type', 'direction', 'score_signal',
                                  'entry_price', 'exit_price', 'pnl_percent', 'pnl_dollars',
                                  'rr_realized', 'status', 'confidence']].copy()
        
        # Formater les colonnes
        display_df['datetime'] = display_df['datetime'].dt.strftime('%Y-%m-%d %H:%M')
        display_df['pnl_percent'] = display_df['pnl_percent'].apply(
            lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A"
        )
        display_df['pnl_dollars'] = display_df['pnl_dollars'].apply(
            lambda x: f"${x:+,.0f}" if pd.notna(x) else "N/A"
        )
        display_df['rr_realized'] = display_df['rr_realized'].apply(
            lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
        )
        
        # Afficher avec couleurs
        st.dataframe(
            display_df,
            use_container_width=True,
            height=500
        )
        
        # Détails sur sélection
        selected_indices = st.multiselect(
            "Sélectionner des trades pour voir les détails",
            filtered_df.index.tolist()
        )
        
        if selected_indices:
            for idx in selected_indices:
                trade = filtered_df.loc[idx]
                
                with st.expander(f"Détails Trade #{idx}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Notes:**", trade['notes'] if pd.notna(trade['notes']) else "Aucune")
                        st.write("**Erreurs:**", trade['mistakes'] if pd.notna(trade['mistakes']) else "Aucune")
                    
                    with col2:
                        st.write("**Leçons:**", trade['lessons'] if pd.notna(trade['lessons']) else "Aucune")
                        
                        # Afficher le screenshot si disponible
                        if pd.notna(trade.get('screenshot_path')) and os.path.exists(trade['screenshot_path']):
                            st.image(trade['screenshot_path'], caption="Screenshot du setup")


def display_statistics(journal):
    """Affiche les statistiques détaillées"""
    
    st.subheader("📊 Statistiques de Trading")
    
    stats = journal.get_statistics()
    
    if not stats:
        st.info("Pas assez de données pour calculer les statistiques")
        return
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Trades", stats.get('total_trades', 0))
        st.metric("Trades Ouverts", stats.get('open_trades', 0))
    
    with col2:
        st.metric("Win Rate", f"{stats.get('win_rate', 0):.1f}%")
        st.metric("Profit Factor", f"{stats.get('profit_factor', 0):.2f}")
    
    with col3:
        st.metric("PnL Total", f"${stats.get('total_pnl', 0):,.0f}")
        st.metric("Sharpe Ratio", f"{stats.get('sharpe_ratio', 0):.2f}")
    
    with col4:
        st.metric("Gain Moyen", f"${stats.get('avg_win', 0):,.0f}")
        st.metric("Perte Moyenne", f"${stats.get('avg_loss', 0):,.0f}")
    
    # Statistiques par setup
    if 'by_setup' in stats and stats['by_setup']:
        st.subheader("📈 Performance par Setup")
        
        setup_data = []
        for setup, setup_stats in stats['by_setup'].items():
            setup_data.append({
                'Setup': setup,
                'Trades': setup_stats['count'],
                'Win Rate': f"{setup_stats['win_rate']:.1f}%",
                'PnL Moyen': f"${setup_stats['avg_pnl']:,.0f}",
                'PnL Total': f"${setup_stats['total_pnl']:,.0f}"
            })
        
        setup_df = pd.DataFrame(setup_data)
        st.dataframe(setup_df, use_container_width=True)
        
        # Graphiques
        col1, col2 = st.columns(2)
        
        with col1:
            # Win rate par setup
            fig = px.bar(
                setup_df,
                x='Setup',
                y=[float(x.strip('%')) for x in setup_df['Win Rate']],
                title="Win Rate par Setup",
                labels={'y': 'Win Rate (%)'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # PnL par setup
            fig = px.bar(
                setup_df,
                x='Setup',
                y=[float(x.replace('$', '').replace(',', '')) for x in setup_df['PnL Total']],
                title="PnL Total par Setup",
                labels={'y': 'PnL ($)'},
                color=[float(x.replace('$', '').replace(',', '')) for x in setup_df['PnL Total']],
                color_continuous_scale='RdYlGn'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Distribution des R:R
    if not journal.trades_df.empty:
        closed_trades = journal.trades_df[journal.trades_df['status'] == 'Closed']
        
        if not closed_trades.empty and 'rr_realized' in closed_trades.columns:
            st.subheader("📊 Distribution des R:R")
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.histogram(
                    closed_trades,
                    x='rr_realized',
                    nbins=20,
                    title="Distribution des R:R Réalisés"
                )
                fig.add_vline(x=0, line_dash="dash", line_color="red")
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Comparaison R:R prévu vs réalisé
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=closed_trades['rr_planned'],
                    y=closed_trades['rr_realized'],
                    mode='markers',
                    marker=dict(
                        size=10,
                        color=closed_trades['pnl_percent'],
                        colorscale='RdYlGn',
                        showscale=True
                    ),
                    text=closed_trades['setup_type'],
                    hovertemplate='%{text}<br>Prévu: %{x:.2f}<br>Réalisé: %{y:.2f}'
                ))
                
                # Ligne de référence
                max_val = max(closed_trades['rr_planned'].max(), closed_trades['rr_realized'].max())
                fig.add_trace(go.Scatter(
                    x=[0, max_val],
                    y=[0, max_val],
                    mode='lines',
                    line=dict(dash='dash', color='gray'),
                    name='Parfait'
                ))
                
                fig.update_layout(
                    title="R:R Prévu vs Réalisé",
                    xaxis_title="R:R Prévu",
                    yaxis_title="R:R Réalisé"
                )
                
                st.plotly_chart(fig, use_container_width=True)


def display_performance_analysis(journal):
    """Analyse de performance avancée"""
    
    st.subheader("💹 Analyse de Performance")
    
    # Equity Curve
    equity_curve = journal.calculate_equity_curve()
    
    if not equity_curve.empty:
        st.subheader("📈 Courbe d'Équité")
        
        fig = go.Figure()
        
        # Courbe cumulative
        fig.add_trace(go.Scatter(
            x=equity_curve['datetime'],
            y=equity_curve['cumulative_pnl'],
            mode='lines',
            name='PnL Cumulé',
            line=dict(color='blue', width=2)
        ))
        
        # Marquer les trades individuels
        positive_trades = equity_curve[equity_curve['pnl_dollars'] > 0]
        negative_trades = equity_curve[equity_curve['pnl_dollars'] < 0]
        
        fig.add_trace(go.Scatter(
            x=positive_trades['datetime'],
            y=positive_trades['cumulative_pnl'],
            mode='markers',
            marker=dict(color='green', size=8),
            name='Trades Gagnants'
        ))
        
        fig.add_trace(go.Scatter(
            x=negative_trades['datetime'],
            y=negative_trades['cumulative_pnl'],
            mode='markers',
            marker=dict(color='red', size=8),
            name='Trades Perdants'
        ))
        
        # Ligne de référence à 0
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        
        fig.update_layout(
            title="Évolution du Capital",
            xaxis_title="Date",
            yaxis_title="PnL Cumulé ($)",
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Analyse des drawdowns
        drawdown_stats = journal.get_drawdown_analysis()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Drawdown Actuel", 
                     f"${drawdown_stats.get('current_drawdown', 0):,.0f}")
        
        with col2:
            st.metric("Drawdown Maximum", 
                     f"${drawdown_stats.get('max_drawdown', 0):,.0f}")
        
        with col3:
            if drawdown_stats.get('max_drawdown_date'):
                st.metric("Date du Max DD", 
                         drawdown_stats['max_drawdown_date'].strftime('%Y-%m-%d'))
    
    # Analyse mensuelle
    if not journal.trades_df.empty:
        closed_trades = journal.trades_df[journal.trades_df['status'] == 'Closed'].copy()
        
        if not closed_trades.empty:
            st.subheader("📅 Performance Mensuelle")
            
            # Grouper par mois
            closed_trades['month'] = closed_trades['datetime'].dt.to_period('M')
            monthly_stats = closed_trades.groupby('month').agg({
                'pnl_dollars': ['sum', 'count'],
                'pnl_percent': 'mean'
            }).round(2)
            
            # Créer un heatmap mensuel
            if len(monthly_stats) > 1:
                fig = px.bar(
                    x=monthly_stats.index.astype(str),
                    y=monthly_stats['pnl_dollars']['sum'],
                    title="PnL Mensuel",
                    labels={'x': 'Mois', 'y': 'PnL ($)'},
                    color=monthly_stats['pnl_dollars']['sum'],
                    color_continuous_scale='RdYlGn'
                )
                
                st.plotly_chart(fig, use_container_width=True)
    
    # Analyse par jour de la semaine
    if not journal.trades_df.empty:
        st.subheader("📊 Performance par Jour de la Semaine")
        
        trades_with_day = journal.trades_df.copy()
        trades_with_day['day_of_week'] = trades_with_day['datetime'].dt.day_name()
        
        day_stats = trades_with_day.groupby('day_of_week').agg({
            'pnl_dollars': ['mean', 'sum', 'count']
        }).round(2)
        
        if not day_stats.empty:
            days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            day_stats = day_stats.reindex(days_order, fill_value=0)
            
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=days_order,
                y=day_stats['pnl_dollars']['mean'],
                name='PnL Moyen',
                marker_color='lightblue'
            ))
            
            fig.update_layout(
                title="PnL Moyen par Jour de la Semaine",
                xaxis_title="Jour",
                yaxis_title="PnL Moyen ($)"
            )
            
            st.plotly_chart(fig, use_container_width=True)


def display_export_import(journal):
    """Gestion des exports et imports"""
    
    st.subheader("📋 Export / Import des Données")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📥 Export")
        
        if not journal.trades_df.empty:
            # Préparer les données pour export
            export_df = journal.trades_df.copy()
            export_df['datetime'] = export_df['datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # CSV complet
            csv = export_df.to_csv(index=False)
            st.download_button(
                label="💾 Télécharger Journal Complet (CSV)",
                data=csv,
                file_name=f"trading_journal_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
            
            # Rapport de synthèse
            stats = journal.get_statistics()
            
            report = f"""
# RAPPORT DE TRADING
Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## STATISTIQUES GLOBALES
- Total Trades: {stats.get('total_trades', 0)}
- Win Rate: {stats.get('win_rate', 0):.1f}%
- PnL Total: ${stats.get('total_pnl', 0):,.0f}
- Profit Factor: {stats.get('profit_factor', 0):.2f}
- Sharpe Ratio: {stats.get('sharpe_ratio', 0):.2f}

## MOYENNES
- Gain Moyen: ${stats.get('avg_win', 0):,.0f}
- Perte Moyenne: ${stats.get('avg_loss', 0):,.0f}
- R:R Moyen Prévu: {stats.get('avg_rr_planned', 0):.2f}
- R:R Moyen Réalisé: {stats.get('avg_rr_realized', 0):.2f}

## RECORDS
- Plus Gros Gain: ${stats.get('largest_win', 0):,.0f}
- Plus Grosse Perte: ${stats.get('largest_loss', 0):,.0f}
            """
            
            st.download_button(
                label="📊 Télécharger Rapport (TXT)",
                data=report,
                file_name=f"trading_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain"
            )
        else:
            st.info("Aucune donnée à exporter")
    
    with col2:
        st.markdown("### 📤 Import")
        
        uploaded_file = st.file_uploader(
            "Importer un journal CSV",
            type=['csv'],
            help="Format: même structure que l'export"
        )
        
        if uploaded_file:
            try:
                import_df = pd.read_csv(uploaded_file)
                import_df['datetime'] = pd.to_datetime(import_df['datetime'])
                
                st.write(f"Fichier contient {len(import_df)} trades")
                
                if st.button("Confirmer l'import", type="primary"):
                    # Fusionner avec les données existantes
                    journal.trades_df = pd.concat([journal.trades_df, import_df], ignore_index=True)
                    journal.trades_df = journal.trades_df.drop_duplicates()
                    journal.save_trades()
                    
                    st.success(f"✅ {len(import_df)} trades importés!")
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Erreur lors de l'import: {str(e)}")


def display_no_trade_form(journal, tz_name):
    """Formulaire pour enregistrer un jour sans trade"""
    
    st.subheader("🗓️ Enregistrer un Jour Sans Trade")
    st.info("💪 Valorisez votre discipline en documentant les jours où vous avez résisté à la tentation de trader")
    
    with st.form("no_trade_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            nt_date = st.date_input(
                "Date du jour sans trade",
                value=datetime.now().date(),
                help="Date où vous n'avez pas tradé"
            )
            
            nt_conf = st.slider(
                "Niveau de Discipline",
                min_value=1,
                max_value=5,
                value=4,
                help="1=Très difficile, 5=Facile de résister"
            )
            
            setup_type = st.selectbox(
                "Setup rejeté (optionnel)",
                ["Aucun", "Bottom 4H", "Top 4H", "Bottom 1H", "Top 1H", 
                 "Bottom Daily", "Top Daily", "Scalp", "Swing"],
                help="Quel setup aviez-vous identifié mais rejeté?"
            )
        
        with col2:
            nt_tempt = st.slider(
                "Niveau de Tentation",
                min_value=0,
                max_value=10,
                value=3,
                help="0=Aucune tentation, 10=Très tenté de trader"
            )
            
            nt_hours = st.number_input(
                "Heures d'observation",
                min_value=0.0,
                max_value=24.0,
                step=0.5,
                value=0.0,
                help="Combien d'heures avez-vous observé les marchés?"
            )
            
            market_context = st.selectbox(
                "Contexte de Marché",
                ["Bull Market", "Bear Market", "Range", "Breakout", 
                 "Consolidation", "High Volatility", "Low Volatility"],
                help="Conditions générales du marché"
            )
        
        with col3:
            reasons = st.multiselect(
                "Raisons du non-trade",
                ["Setup non valide", "Conditions pas claires", "Fatigue", 
                 "News importantes", "Volatilité excessive", "Manque de confiance",
                 "Limite de trades atteinte", "Risk management", "Autre"],
                help="Pourquoi n'avez-vous pas tradé?"
            )
            
            score_signal = st.slider(
                "Score du meilleur signal rejeté",
                min_value=0.0,
                max_value=10.0,
                value=0.0,
                step=0.5,
                help="Quel était le score du signal que vous avez choisi de ne pas prendre?"
            )
        
        # Zone de texte pour les notes
        notes = st.text_area(
            "Notes et Réflexions",
            height=150,
            placeholder="Décrivez votre état d'esprit, les signaux que vous avez vus mais ignorés, vos raisons...",
            help="Documentez votre processus de décision"
        )
        
        # Formatage des notes avec les infos supplémentaires
        formatted_notes = f"Tentation: {nt_tempt}/10 | Observation: {nt_hours}h | Raisons: {', '.join(reasons)} | {notes}"
        
        col1, col2 = st.columns(2)
        
        with col1:
            submitted = st.form_submit_button(
                "💾 Enregistrer le Jour Sans Trade",
                use_container_width=True,
                type="primary"
            )
        
        with col2:
            st.metric(
                "Jours sans trade ce mois",
                len(journal.trades_df[
                    (journal.trades_df['type'] == 'NoTrade') & 
                    (pd.to_datetime(journal.trades_df['datetime']).dt.month == datetime.now().month) &
                    (journal.trades_df['is_deleted'] == False)
                ])
            )
        
        if submitted:
            no_trade_data = {
                'datetime': datetime.combine(nt_date, datetime.min.time()),
                'setup_type': setup_type if setup_type != "Aucun" else "NoTrade",
                'score_signal': score_signal,
                'confidence': nt_conf,
                'market_context': market_context,
                'notes': formatted_notes,
                'position_size': 0,
                'max_drawdown': 0,
                'max_profit': 0,
                'duration_hours': nt_hours
            }
            
            if journal.add_no_trade_day(no_trade_data):
                st.success("✅ Jour sans trade enregistré! Bravo pour votre discipline! 💪")
                st.balloons()
            else:
                st.error("❌ Erreur lors de l'enregistrement")


def display_trade_management(journal):
    """Interface pour gérer (supprimer/restaurer) les trades"""
    
    st.subheader("🗑️ Gestion des Trades")
    
    # Sélection du type d'action
    action = st.radio(
        "Action à effectuer",
        ["Supprimer un trade", "Restaurer un trade archivé", "Supprimer la dernière entrée"],
        horizontal=True
    )
    
    if action == "Supprimer un trade":
        st.markdown("### 🧹 Supprimer une entrée du journal")
        
        # Filtrer les trades actifs seulement
        active_trades = journal.get_active_trades()
        
        if len(active_trades) > 0:
            # Colonnes à afficher
            show_cols = ['datetime', 'type', 'setup_type', 'direction', 'entry_price', 'pnl_dollars', 'status']
            available_cols = [col for col in show_cols if col in active_trades.columns]
            
            # Afficher un aperçu des trades récents
            st.dataframe(
                active_trades[available_cols].tail(15),
                use_container_width=True,
                height=400
            )
            
            # Créer des options lisibles pour la sélection
            options = []
            for idx, row in active_trades.iterrows():
                if row['type'] == 'NoTrade':
                    option = f"{row['id'][:8]} | {row['datetime'].strftime('%Y-%m-%d')} | Jour Sans Trade | {row.get('notes', '')[:30]}..."
                else:
                    option = f"{row['id'][:8]} | {row['datetime'].strftime('%Y-%m-%d %H:%M')} | {row['type']} | {row.get('setup_type', '')} | {row.get('direction', '')} | PnL: ${row.get('pnl_dollars', 0):.0f}"
                options.append(option)
            
            selected = st.selectbox(
                "Sélectionnez l'entrée à supprimer",
                options,
                help="Choisissez le trade ou jour sans trade à supprimer"
            )
            
            if selected:
                # Extraire l'ID du trade sélectionné
                sel_id = selected.split(" | ")[0]
                full_id = active_trades[active_trades['id'].str.startswith(sel_id)]['id'].iloc[0]
                
                # Options de suppression
                col1, col2 = st.columns(2)
                
                with col1:
                    deletion_type = st.radio(
                        "Type de suppression",
                        ["Archiver (réversible)", "Supprimer définitivement"],
                        help="L'archivage permet de restaurer plus tard"
                    )
                
                with col2:
                    st.warning("⚠️ La suppression définitive est irréversible!")
                
                confirm = st.checkbox("Je confirme vouloir supprimer cette entrée")
                
                if st.button("🗑️ Supprimer", type="primary", disabled=not confirm):
                    if confirm:
                        permanent = deletion_type == "Supprimer définitivement"
                        if journal.delete_trade(full_id, permanent=permanent):
                            if permanent:
                                st.success("✅ Entrée supprimée définitivement")
                            else:
                                st.success("✅ Entrée archivée (peut être restaurée)")
                            st.rerun()
                        else:
                            st.error("❌ Erreur lors de la suppression")
        else:
            st.info("Aucun trade actif dans le journal")
    
    elif action == "Restaurer un trade archivé":
        st.markdown("### ♾️ Restaurer un trade archivé")
        
        # Afficher les trades archivés
        archived_trades = journal.trades_df[journal.trades_df['is_deleted'] == True]
        
        if len(archived_trades) > 0:
            st.write(f"**{len(archived_trades)} trade(s) archivé(s) trouvé(s)**")
            
            # Afficher les trades archivés
            show_cols = ['datetime', 'type', 'setup_type', 'direction', 'entry_price', 'pnl_dollars']
            available_cols = [col for col in show_cols if col in archived_trades.columns]
            
            st.dataframe(
                archived_trades[available_cols],
                use_container_width=True
            )
            
            # Sélection du trade à restaurer
            options = []
            for idx, row in archived_trades.iterrows():
                if row['type'] == 'NoTrade':
                    option = f"{row['id'][:8]} | {row['datetime'].strftime('%Y-%m-%d')} | Jour Sans Trade"
                else:
                    option = f"{row['id'][:8]} | {row['datetime'].strftime('%Y-%m-%d %H:%M')} | {row.get('setup_type', '')} | PnL: ${row.get('pnl_dollars', 0):.0f}"
                options.append(option)
            
            selected = st.selectbox(
                "Sélectionnez l'entrée à restaurer",
                options
            )
            
            if selected and st.button("♾️ Restaurer", type="primary"):
                sel_id = selected.split(" | ")[0]
                full_id = archived_trades[archived_trades['id'].str.startswith(sel_id)]['id'].iloc[0]
                
                if journal.restore_trade(full_id):
                    st.success("✅ Trade restauré avec succès!")
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de la restauration")
        else:
            st.info("Aucun trade archivé")
    
    else:  # Supprimer la dernière entrée
        st.markdown("### ⏪ Supprimer la dernière entrée")
        st.info("💡 Utile en cas d'erreur de saisie immédiate")
        
        active_trades = journal.get_active_trades()
        
        if len(active_trades) > 0:
            last_trade = active_trades.iloc[-1]
            
            # Afficher les détails de la dernière entrée
            st.write("**Dernière entrée:**")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"Date: {last_trade['datetime'].strftime('%Y-%m-%d %H:%M')}")
                st.write(f"Type: {last_trade['type']}")
            
            with col2:
                if last_trade['type'] == 'Trade':
                    st.write(f"Setup: {last_trade.get('setup_type', 'N/A')}")
                    st.write(f"Direction: {last_trade.get('direction', 'N/A')}")
            
            with col3:
                if last_trade['type'] == 'Trade':
                    st.write(f"Entry: ${last_trade.get('entry_price', 0):.0f}")
                    st.write(f"PnL: ${last_trade.get('pnl_dollars', 0):.0f}")
            
            if st.button("⏪ Supprimer la dernière entrée", type="primary"):
                if journal.delete_trade(last_trade['id'], permanent=True):
                    st.success("✅ Dernière entrée supprimée")
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de la suppression")
        else:
            st.info("Aucune entrée dans le journal")
    
    # Statistiques de gestion
    st.markdown("---")
    st.markdown("### 📊 Statistiques de Gestion")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_entries = len(journal.trades_df)
        st.metric("Total Entrées", total_entries)
    
    with col2:
        active_entries = len(journal.get_active_trades())
        st.metric("Entrées Actives", active_entries)
    
    with col3:
        archived_entries = len(journal.trades_df[journal.trades_df['is_deleted'] == True])
        st.metric("Entrées Archivées", archived_entries)
    
    with col4:
        no_trade_days = len(journal.trades_df[
            (journal.trades_df['type'] == 'NoTrade') & 
            (journal.trades_df['is_deleted'] == False)
        ])
        st.metric("Jours Sans Trade", no_trade_days)
