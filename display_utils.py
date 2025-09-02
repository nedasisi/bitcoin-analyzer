"""
Module d'affichage amélioré avec heure exacte des bottoms
"""

import streamlit as st
import pandas as pd

def display_bottoms_with_exact_time(bottoms_tz, selected_tz_name, selected_timeframe, TIMEFRAMES, DAYS_FR):
    """
    Affiche le tableau des bottoms avec l'heure exacte estimée
    """
    st.header(f"Liste Détaillée des Bottoms ({selected_tz_name})")
    
    # Explication améliorée
    with st.expander("📖 Comprendre l'affichage temporel", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            **🕐 Précision Temporelle**
            - Timeframe: **{selected_timeframe}**
            - Précision: **±{TIMEFRAMES[selected_timeframe]}**
            - Fuseau: **{selected_tz_name}**
            """)
        
        with col2:
            st.markdown("""
            **📊 Colonnes Temps**
            - **Heure Bougie**: Début de la bougie
            - **Heure Exacte**: Estimation du vrai minimum
            - **Différence**: Écart en minutes
            """)
        
        with col3:
            st.markdown("""
            **🎯 Méthode d'Estimation**
            - Analyse OHLC de chaque bougie
            - Position du low selon le pattern
            - Plus précis avec petit timeframe
            """)
    
    if not bottoms_tz.empty:
        # Préparer l'affichage
        display_df = bottoms_tz.copy()
        
        # Date et heures
        display_df['Date'] = display_df.index.strftime('%Y-%m-%d')
        display_df['Heure Bougie'] = display_df.index.strftime('%H:%M')
        
        # Heure exacte si disponible
        if 'exact_time' in display_df.columns:
            # Convertir en datetime si nécessaire
            if not pd.api.types.is_datetime64_any_dtype(display_df['exact_time']):
                display_df['exact_time'] = pd.to_datetime(display_df['exact_time'])
            
            display_df['Heure Exacte'] = display_df['exact_time'].dt.strftime('%H:%M')
            
            # Calculer la différence
            time_diff = (display_df['exact_time'] - display_df.index).dt.total_seconds() / 60
            display_df['Diff (min)'] = time_diff.round().astype(int)
            
            # Indicateur visuel de la différence
            def format_diff(minutes):
                if abs(minutes) < 30:
                    return f"✅ {minutes:+d}'"
                elif abs(minutes) < 60:
                    return f"⚠️ {minutes:+d}'"
                else:
                    return f"⚠️ {minutes:+d}'"
            
            display_df['Précision'] = display_df['Diff (min)'].apply(format_diff)
        else:
            display_df['Heure Exacte'] = display_df['Heure Bougie']
            display_df['Précision'] = "N/A"
        
        # Autres colonnes
        display_df['Jour'] = display_df['day_of_week'].map(DAYS_FR)
        display_df['Prix'] = display_df['price'].apply(lambda x: f"${x:,.0f}")
        
        # Type avec emoji
        if 'type' in display_df.columns:
            type_emojis = {
                'simple': '🟡 Simple',
                'confirmed': '🟠 Confirmé',
                'major': '🔴 Majeur'
            }
            display_df['Type'] = display_df['type'].map(type_emojis)
        
        # Colonnes à afficher
        columns = ['Date', 'Jour', 'Heure Bougie', 'Heure Exacte', 'Précision', 'Prix']
        
        if 'Type' in display_df.columns:
            columns.append('Type')
        
        # Filtres
        col1, col2, col3 = st.columns(3)
        
        with col1:
            filter_day = st.selectbox(
                "Filtrer par jour",
                ["Tous"] + list(DAYS_FR.values())
            )
        
        with col2:
            if 'Type' in display_df.columns:
                filter_type = st.selectbox(
                    "Filtrer par type",
                    ["Tous", "🟡 Simple", "🟠 Confirmé", "🔴 Majeur"]
                )
            else:
                filter_type = "Tous"
        
        with col3:
            show_exact_only = st.checkbox("Montrer seulement les heures exactes", value=True)
        
        # Appliquer les filtres
        filtered_df = display_df.copy()
        
        if filter_day != "Tous":
            filtered_df = filtered_df[filtered_df['Jour'] == filter_day]
        
        if filter_type != "Tous" and 'Type' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Type'] == filter_type]
        
        # Option pour masquer la colonne bougie si on a l'heure exacte
        if show_exact_only and 'Heure Exacte' in columns:
            columns.remove('Heure Bougie')
        
        # Afficher le tableau
        st.dataframe(
            filtered_df[columns].sort_index(ascending=False),
            use_container_width=True,
            height=500
        )
        
        # Statistiques sur la précision
        if 'Diff (min)' in display_df.columns:
            st.subheader("📊 Statistiques de Précision")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                avg_diff = display_df['Diff (min)'].abs().mean()
                st.metric("Écart Moyen", f"{avg_diff:.0f} minutes")
            
            with col2:
                median_diff = display_df['Diff (min)'].abs().median()
                st.metric("Écart Médian", f"{median_diff:.0f} minutes")
            
            with col3:
                max_diff = display_df['Diff (min)'].abs().max()
                st.metric("Écart Max", f"{max_diff:.0f} minutes")
        
        # Export CSV
        csv = filtered_df[columns].to_csv(index=False)
        st.download_button(
            label="📥 Télécharger CSV avec heures exactes",
            data=csv,
            file_name=f"bitcoin_bottoms_exact_{selected_tz_name}_{selected_timeframe}.csv",
            mime="text/csv"
        )
    else:
        st.warning("Aucun bottom détecté avec les paramètres actuels")
    
    return