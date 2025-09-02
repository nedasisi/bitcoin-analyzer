"""
Nouvel onglet amélioré pour l'analyse complète des heures exactes
avec support batch et cache persistant
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import time
import os

def display_exact_time_tab_with_full_analysis(bottoms_tz, selected_tz, selected_tz_name, selected_timeframe):
    """
    Onglet amélioré avec option d'analyse complète de tous les bottoms
    """
    from exact_bottom_finder import ExactBottomFinder
    from batch_analyzer import BatchExactTimeAnalyzer
    
    st.header("🎯 Calcul de l'Heure Exacte des Bottoms (Précision 1 minute)")
    
    # Tabs pour différents modes
    mode_tab1, mode_tab2, mode_tab3 = st.tabs([
        "⚡ Analyse Rapide (1-20 bottoms)",
        "🔥 Analyse Complète (TOUS les bottoms)",
        "📊 Cache & Statistiques"
    ])
    
    with mode_tab1:
        # Mode rapide existant (20 bottoms max)
        display_quick_analysis(bottoms_tz, selected_tz, selected_tz_name, selected_timeframe)
    
    with mode_tab2:
        # Nouveau mode : Analyse complète
        display_full_analysis(bottoms_tz, selected_tz, selected_tz_name, selected_timeframe)
    
    with mode_tab3:
        # Gestion du cache
        display_cache_management()

def display_full_analysis(bottoms_tz, selected_tz, selected_tz_name, selected_timeframe):
    """
    Analyse complète de TOUS les bottoms avec batch processing
    """
    st.subheader("🔥 Analyse Complète - Tous les Bottoms depuis 2019")
    
    # Statistiques
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Bottoms", len(bottoms_tz))
    
    with col2:
        date_range_str = f"{bottoms_tz.index.min().strftime('%Y-%m-%d')} à {bottoms_tz.index.max().strftime('%Y-%m-%d')}"
        st.metric("Période", date_range_str)
    
    with col3:
        estimated_time = len(bottoms_tz) * 1.5 / 60  # 1.5 secondes par bottom
        st.metric("Temps estimé", f"{estimated_time:.1f} minutes")
    
    # Options de traitement
    st.subheader("⚙️ Options de Traitement")
    
    col1, col2 = st.columns(2)
    
    with col1:
        batch_size = st.slider(
            "Taille des batches",
            min_value=5,
            max_value=50,
            value=20,
            help="Plus grand = plus rapide mais plus de risque d'erreur API"
        )
        
        use_cache = st.checkbox(
            "Utiliser le cache",
            value=True,
            help="Réutilise les résultats déjà calculés"
        )
    
    with col2:
        delay = st.slider(
            "Délai entre requêtes (secondes)",
            min_value=0.5,
            max_value=3.0,
            value=1.0,
            step=0.5,
            help="Plus long = moins d'erreurs API"
        )
        
        filter_type = st.selectbox(
            "Types à analyser",
            ["Tous", "Majeurs seulement", "Confirmés et Majeurs"],
            help="Filtrer par type de bottom"
        )
    
    # Filtrer si nécessaire
    bottoms_to_process = bottoms_tz.copy()
    
    if filter_type == "Majeurs seulement" and 'type' in bottoms_to_process.columns:
        bottoms_to_process = bottoms_to_process[bottoms_to_process['type'] == 'major']
    elif filter_type == "Confirmés et Majeurs" and 'type' in bottoms_to_process.columns:
        bottoms_to_process = bottoms_to_process[bottoms_to_process['type'].isin(['confirmed', 'major'])]
    
    st.info(f"📊 {len(bottoms_to_process)} bottoms à analyser ({filter_type})")
    
    # Avertissements
    if len(bottoms_to_process) > 100:
        st.warning(f"""
        ⚠️ **Attention**: Analyser {len(bottoms_to_process)} bottoms prendra environ {len(bottoms_to_process) * delay / 60:.1f} minutes.
        
        **Recommandations**:
        - L'analyse continuera même si vous fermez la page
        - Les résultats sont sauvegardés progressivement
        - Vous pouvez reprendre l'analyse plus tard
        """)
    
    # Bouton pour lancer l'analyse complète
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🚀 LANCER L'ANALYSE COMPLÈTE", type="primary", use_container_width=True):
            run_full_batch_analysis(bottoms_to_process, batch_size, delay, use_cache, selected_tz, selected_tz_name)
    
    with col2:
        if st.button("⏸️ Voir Résultats Partiels", use_container_width=True):
            show_partial_results()
    
    with col3:
        if st.button("🗑️ Effacer le Cache", use_container_width=True):
            if st.confirm("Êtes-vous sûr de vouloir effacer tout le cache?"):
                analyzer = BatchExactTimeAnalyzer()
                analyzer.clear_cache()
                st.success("Cache effacé!")

def run_full_batch_analysis(bottoms_df, batch_size, delay, use_cache, selected_tz, selected_tz_name):
    """
    Lance l'analyse batch complète
    """
    from batch_analyzer import BatchExactTimeAnalyzer
    
    # Initialiser l'analyseur
    analyzer = BatchExactTimeAnalyzer()
    
    # Container pour les mises à jour
    progress_container = st.container()
    
    with progress_container:
        # Barre de progression
        progress_bar = st.progress(0)
        status_text = st.empty()
        metrics_container = st.empty()
        
        # Callback pour mise à jour
        def update_progress(processed, total, message):
            progress = processed / total
            progress_bar.progress(progress)
            status_text.text(f"[{processed}/{total}] {message}")
            
            # Afficher les métriques
            with metrics_container.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Traités", f"{processed}/{total}")
                with col2:
                    percentage = (processed/total) * 100
                    st.metric("Progression", f"{percentage:.1f}%")
                with col3:
                    remaining = (total - processed) * delay
                    st.metric("Temps restant", f"{remaining/60:.1f} min")
        
        # Lancer l'analyse
        try:
            results_df, errors = analyzer.analyze_batch(
                bottoms_df,
                batch_size=batch_size,
                delay=delay,
                progress_callback=update_progress
            )
            
            # Effacer la progression
            progress_bar.empty()
            status_text.empty()
            metrics_container.empty()
            
            # Afficher les résultats
            if not results_df.empty:
                st.success(f"✅ Analyse terminée! {len(results_df)} bottoms analysés avec succès.")
                
                # Convertir les timestamps au fuseau sélectionné
                if selected_tz != 'UTC':
                    # Vérifier si les timestamps ont déjà un timezone
                    results_df['exact_time'] = pd.to_datetime(results_df['exact_time'])
                    results_df['timestamp'] = pd.to_datetime(results_df['timestamp'])
                    
                    # Si pas de timezone, localiser en UTC puis convertir
                    if results_df['exact_time'].dt.tz is None:
                        results_df['exact_time'] = results_df['exact_time'].dt.tz_localize('UTC').dt.tz_convert(selected_tz)
                    else:
                        # Si déjà un timezone, juste convertir
                        results_df['exact_time'] = results_df['exact_time'].dt.tz_convert(selected_tz)
                    
                    if results_df['timestamp'].dt.tz is None:
                        results_df['timestamp'] = results_df['timestamp'].dt.tz_localize('UTC').dt.tz_convert(selected_tz)
                    else:
                        results_df['timestamp'] = results_df['timestamp'].dt.tz_convert(selected_tz)
                
                # Préparer l'affichage
                display_df = pd.DataFrame({
                    'Date': results_df['timestamp'].dt.strftime('%Y-%m-%d'),
                    'Heure Bougie': results_df['timestamp'].dt.strftime('%H:%M'),
                    'Heure Exacte': results_df['exact_time'].dt.strftime('%H:%M:%S'),
                    'Écart (min)': ((results_df['exact_time'] - results_df['timestamp']).dt.total_seconds() / 60).round(),
                    'Prix Original': results_df['original_price'].apply(lambda x: f"${x:,.0f}"),
                    'Prix Exact': results_df['exact_price'].apply(lambda x: f"${x:,.0f}"),
                    'Volume': results_df['volume_at_bottom'].apply(lambda x: f"{x:,.0f}")
                })
                
                # Afficher le tableau
                st.subheader("📊 Résultats Complets")
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    height=600
                )
                
                # Statistiques globales
                st.subheader("📈 Statistiques Globales")
                
                col1, col2, col3, col4 = st.columns(4)
                
                ecarts = display_df['Écart (min)'].abs()
                
                with col1:
                    st.metric("Écart Moyen", f"{ecarts.mean():.0f} min")
                with col2:
                    st.metric("Écart Médian", f"{ecarts.median():.0f} min")
                with col3:
                    precision_30 = (ecarts < 30).sum() / len(ecarts) * 100
                    st.metric("Précision <30min", f"{precision_30:.0f}%")
                with col4:
                    st.metric("Taux de succès", f"{len(results_df)/len(bottoms_df)*100:.1f}%")
                
                # Export complet
                csv = display_df.to_csv(index=False)
                st.download_button(
                    label="📥 Télécharger TOUS les résultats (CSV)",
                    data=csv,
                    file_name=f"bottoms_exact_time_COMPLET_{selected_tz_name}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    type="primary"
                )
            
            # Afficher les erreurs
            if errors:
                with st.expander(f"⚠️ {len(errors)} erreurs"):
                    for error in errors[:20]:  # Limiter l'affichage
                        st.error(f"{error['timestamp']}: {error['error']}")
                    
                    if len(errors) > 20:
                        st.warning(f"... et {len(errors) - 20} autres erreurs")
        
        except Exception as e:
            st.error(f"❌ Erreur lors de l'analyse: {str(e)}")

def show_partial_results():
    """
    Affiche les résultats partiels du cache
    """
    from batch_analyzer import BatchExactTimeAnalyzer
    
    analyzer = BatchExactTimeAnalyzer()
    stats = analyzer.get_statistics()
    
    if stats['total_cached'] > 0:
        st.success(f"📊 {stats['total_cached']} résultats en cache")
        
        # Charger et afficher le cache
        cache_df = pd.DataFrame.from_dict(analyzer.cache, orient='index')
        
        if not cache_df.empty:
            st.dataframe(cache_df.head(50), use_container_width=True)
            
            # Option d'export
            if st.button("📥 Exporter le cache en CSV"):
                file_path = analyzer.export_to_csv()
                st.success(f"Exporté vers: {file_path}")
    else:
        st.info("Aucun résultat en cache pour le moment")

def display_cache_management():
    """
    Gestion et statistiques du cache
    """
    from batch_analyzer import BatchExactTimeAnalyzer
    
    st.subheader("📊 Gestion du Cache")
    
    analyzer = BatchExactTimeAnalyzer()
    stats = analyzer.get_statistics()
    
    # Afficher les statistiques
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Entrées en cache", stats['total_cached'])
    
    with col2:
        st.metric("Taille du cache", f"{stats['cache_size_kb']:.1f} KB")
    
    with col3:
        if stats['oldest_entry'] and stats['newest_entry']:
            st.metric("Période couverte", f"{stats['oldest_entry'][:10]} à {stats['newest_entry'][:10]}")
    
    # Actions
    st.subheader("🔧 Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Rafraîchir les stats"):
            st.rerun()
    
    with col2:
        if st.button("📥 Exporter le cache"):
            file_path = analyzer.export_to_csv('data/exact_times_export.csv')
            st.success(f"Cache exporté vers: {file_path}")
    
    with col3:
        if st.button("🗑️ Vider le cache", type="secondary"):
            if st.confirm("Confirmer la suppression?"):
                analyzer.clear_cache()
                st.success("Cache vidé!")
                st.rerun()
    
    # Afficher un échantillon du cache
    if stats['total_cached'] > 0:
        st.subheader("📋 Échantillon du Cache")
        
        sample_size = st.slider("Nombre d'entrées à afficher", 10, 100, 20)
        
        cache_df = pd.DataFrame.from_dict(analyzer.cache, orient='index')
        if not cache_df.empty:
            st.dataframe(cache_df.head(sample_size), use_container_width=True)

def display_quick_analysis(bottoms_tz, selected_tz, selected_tz_name, selected_timeframe):
    """
    Mode d'analyse rapide (code existant)
    """
    # [Le code existant du mode rapide va ici]
    st.info("Mode d'analyse rapide (1-20 bottoms) - Code existant")
    # ... (copier le code existant du tab7)