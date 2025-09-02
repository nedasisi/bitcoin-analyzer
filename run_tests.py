#!/usr/bin/env python
"""
Script de test complet avant déploiement
Lance tous les tests et vérifie que tout fonctionne
"""

import sys
import os
import subprocess

def run_test(test_name, command):
    """Execute un test et retourne le résultat"""
    print(f"\n{'='*60}")
    print(f"🧪 Test: {test_name}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {test_name}: PASS")
            return True
        else:
            print(f"❌ {test_name}: FAIL")
            print(f"Erreur: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {test_name}: ERREUR - {str(e)}")
        return False

def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║     🚀 TEST COMPLET AVANT DÉPLOIEMENT                    ║
║     Bitcoin Analyzer Pro                                 ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    tests_passed = []
    tests_failed = []
    
    # Test 1: Vérification Python
    if run_test("Version Python", "python --version"):
        tests_passed.append("Version Python")
    else:
        tests_failed.append("Version Python")
    
    # Test 2: Vérification des dépendances
    if run_test("Import des modules", "python -c \"import streamlit; import pandas; import plotly; print('OK')\""):
        tests_passed.append("Import modules")
    else:
        tests_failed.append("Import modules")
    
    # Test 3: Syntaxe du code principal
    if run_test("Syntaxe app.py", "python -m py_compile app.py"):
        tests_passed.append("Syntaxe app.py")
    else:
        tests_failed.append("Syntaxe app.py")
    
    # Test 4: Imports du projet
    test_imports = """
import sys
sys.path.insert(0, '.')
try:
    from config import *
    from bottom_analyzer import BottomAnalyzer
    from top_analyzer import TopAnalyzer
    from trading_journal import TradingJournal
    print('OK')
except Exception as e:
    print(f'ERREUR: {e}')
    sys.exit(1)
"""
    
    with open('test_imports.py', 'w') as f:
        f.write(test_imports)
    
    if run_test("Imports du projet", "python test_imports.py"):
        tests_passed.append("Imports projet")
    else:
        tests_failed.append("Imports projet")
    
    # Nettoyage
    if os.path.exists('test_imports.py'):
        os.remove('test_imports.py')
    
    # Test 5: Création du dossier data
    if not os.path.exists('data'):
        os.makedirs('data')
        print("📁 Dossier 'data' créé")
    
    # Résumé
    print(f"\n{'='*60}")
    print("📊 RÉSUMÉ DES TESTS")
    print(f"{'='*60}")
    
    print(f"\n✅ Tests réussis: {len(tests_passed)}")
    for test in tests_passed:
        print(f"   • {test}")
    
    if tests_failed:
        print(f"\n❌ Tests échoués: {len(tests_failed)}")
        for test in tests_failed:
            print(f"   • {test}")
    
    # Verdict final
    print(f"\n{'='*60}")
    if not tests_failed:
        print("🎉 TOUS LES TESTS PASSENT ! Prêt pour le déploiement.")
        print("\n🚀 Prochaines étapes:")
        print("1. git add .")
        print("2. git commit -m 'Ready for deployment'")
        print("3. git push origin main")
        print("4. Deploy sur Streamlit Cloud")
    else:
        print("⚠️ CERTAINS TESTS ONT ÉCHOUÉ. Corrige les erreurs avant le déploiement.")
    print(f"{'='*60}\n")
    
    return 0 if not tests_failed else 1

if __name__ == "__main__":
    sys.exit(main())