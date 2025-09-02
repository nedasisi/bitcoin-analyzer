"""
Système d'authentification simple pour Streamlit
"""

import streamlit as st
import hashlib

def check_password():
    """Retourne True si l'utilisateur est authentifié"""
    
    def password_entered():
        """Vérifie le mot de passe"""
        if hashlib.sha256(st.session_state["password"].encode()).hexdigest() == st.secrets.get("auth", {}).get("password_hash", ""):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    # Première visite
    if "password_correct" not in st.session_state:
        st.text_input(
            "Mot de passe", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        return False
    
    # Mot de passe incorrect
    elif not st.session_state["password_correct"]:
        st.text_input(
            "Mot de passe", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("😕 Mot de passe incorrect")
        return False
    
    # Mot de passe correct
    else:
        return True

def require_auth():
    """Décorateur pour protéger une page"""
    if not check_password():
        st.stop()
