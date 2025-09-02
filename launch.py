#!/usr/bin/env python
"""
Script de lancement direct pour Bitcoin Analyzer
Utilise le bon environnement Python automatiquement
"""

import sys
import os
import subprocess

def main():
    print("="*50)
    print("   Bitcoin Analyzer Pro - Launcher")
    print("="*50)
    print()
    
    # Utiliser Python 3.10
    python_exe = sys.executable
    print(f"Python utilisé : {python_exe}")
    print(f"Version : {sys.version}")
    print()
    
    # Installer les dépendances si nécessaire
    print("Vérification des dépendances...")
    try:
        import ccxt
        import streamlit
        print("✅ Toutes les dépendances sont installées")
    except ImportError as e:
        print(f"⚠️ Installation des dépendances manquantes...")
        subprocess.run([python_exe, "-m", "pip", "install", "-r", "requirements.txt"])
    
    print()
    print("🚀 Lancement de l'application...")
    print("-"*50)
    
    # Lancer Streamlit
    subprocess.run([python_exe, "-m", "streamlit", "run", "app.py"])

if __name__ == "__main__":
    main()