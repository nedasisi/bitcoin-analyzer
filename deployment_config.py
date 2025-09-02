"""
Configuration automatique pour détection du mode de déploiement
"""

import os
import streamlit as st

# Détection automatique de l'environnement
def is_deployed():
    """Détecte si l'app tourne sur Streamlit Cloud"""
    return (
        os.environ.get('STREAMLIT_RUNTIME_ENV') == 'cloud' or
        'streamlit.app' in os.environ.get('STREAMLIT_URL', '') or
        os.environ.get('USER', '') == 'appuser'
    )

# Mode actuel
IS_PRODUCTION = is_deployed()

# Configuration adaptative
if IS_PRODUCTION:
    # En production : optimisations
    MAX_DAYS_HISTORY = 365  # Limiter à 1 an
    ENABLE_SCREENSHOTS = False  # Pas de screenshots
    USE_CACHE = True  # Utiliser le cache agressivement
    DATA_FOLDER = "/tmp/data"  # Dossier temporaire
else:
    # En local : toutes les fonctionnalités
    MAX_DAYS_HISTORY = 365 * 3
    ENABLE_SCREENSHOTS = True
    USE_CACHE = False
    DATA_FOLDER = "data"

# S'assurer que le dossier data existe
os.makedirs(DATA_FOLDER, exist_ok=True)

# Message de bienvenue selon le mode
def show_deployment_status():
    if IS_PRODUCTION:
        st.sidebar.success("🌐 Mode Cloud - Accès universel")
    else:
        st.sidebar.info("💻 Mode Local - Développement")

# Limite de ressources pour le cloud
CLOUD_LIMITS = {
    'max_datapoints': 10000,
    'cache_ttl': 3600,  # 1 heure
    'max_concurrent_users': 10
}
