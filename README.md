# Bitcoin Analyzer Pro 📊

Un dashboard professionnel complet pour l'analyse des bottoms et tops du Bitcoin avec système de scoring avancé et journal de trading intégré.

## 🎯 Fonctionnalités

### Analyse des Bottoms
- Détection multi-niveaux (simple, confirmé, majeur)
- Scoring avancé 0-10
- Analyse temporelle (heures/jours optimaux)
- Backtest de stratégies
- Heure exacte à la minute près

### Analyse des Tops  
- Système miroir des bottoms
- Double scoring (Multi-critères + GPT-5)
- Filtres anti-fake
- Backtest short
- Confirmation sans look-ahead

### Journal de Trading
- Tracking complet des trades
- Calcul automatique R:R
- Equity curve
- Statistiques détaillées
- Export/Import CSV

## 🚀 Installation

```bash
# Cloner le repo
git clone https://github.com/YOUR_USERNAME/bitcoin-analyzer.git
cd bitcoin-analyzer

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'application
streamlit run app.py
```

## ⚙️ Configuration

Créer un fichier `.streamlit/secrets.toml` avec vos clés API (optionnel) :

```toml
[api]
binance_key = "YOUR_KEY"
binance_secret = "YOUR_SECRET"
```

## 📊 Utilisation

1. Sélectionner le mode d'analyse dans la sidebar
2. Configurer le fuseau horaire et timeframe
3. Explorer les différents onglets
4. Utiliser le journal pour tracker vos trades

## 🔒 Sécurité

- Ne jamais commiter les clés API
- Utiliser les secrets Streamlit en production
- Limiter l'accès si données sensibles

## 📝 License

MIT

## 👤 Auteur

Votre Nom

## 🙏 Remerciements

- Données: Binance/Bitget
- Framework: Streamlit
- Analyse: TA-Lib, ccxt