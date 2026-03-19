# 🔒 TrustNet — Real-Time Anomaly Detection for Import/Export Transactions

> Detecting atypical trade transactions using **Isolation Forest**, **business rules**, and **blockchain traceability** — inspired by the PortNet customs ecosystem.

---

## 🚀 Quick Start (Windows)

```bash
# 1. Cloner le repo
git clone https://github.com/VOTRE_USERNAME/trustnet.git
cd trustnet

# 2. Créer un environnement virtuel
python -m venv venv
venv\Scripts\activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Lancer le pipeline (terminal)
python run.py

# 5. Lancer le dashboard (navigateur)
streamlit run dashboard/app.py
```

---

## 🧠 Architecture

```
Fichier CSV / Excel
        ↓
  ingestion.py     → Lecture, validation des colonnes, nettoyage
        ↓
  features.py      → Unit_Value, profils importateurs, fréquences
        ↓
  model.py         → Isolation Forest (scoring ML)
        ↓
  rules.py         → Règles métier (embargo, valeur nulle, CASH...)
        ↓
  explainer.py     → Explication humaine de chaque anomalie
        ↓
  blockchain.py    → SHA-256 + RSA + QR code par transaction
        ↓
  dashboard/app.py → Visualisation Streamlit
```

---

## 🔍 Détection — Approche hybride

### 1. Isolation Forest (ML)
Chaque transaction reçoit un **score d'anomalie statistique**.  
L'algorithme détecte les transactions qui s'écartent du comportement habituel — sans jamais avoir été entraîné sur des exemples de fraude.

**Dual profiling :**
| Cas | Stratégie |
|-----|-----------|
| Importateur avec ≥ 5 transactions | Profil individuel (comportement typique) |
| Nouvel importateur (cold start) | Profil global pays × catégorie (±2σ) |

### 2. Règles métier
Violations logiques que le ML seul ne détecte pas :
- 🚫 Pays sous embargo (Iran, Syrie, Corée du Nord...)
- 💰 Paiement CASH sur grosse transaction
- ❌ Valeur ou quantité déclarée = 0
- ⚖️ Ratio valeur/poids incohérent
- 🔴 Combinaison (pays, catégorie) interdite

### 3. Score final TrustNet
```
Score final = 50% × Score ML + 35% × Score règles + 15% × Nb explications
```

| Score | Niveau |
|-------|--------|
| ≥ 60 | 🔴 Risque Élevé |
| 30–60 | 🟠 Risque Moyen |
| < 30 | 🟢 Risque Faible |

---

## 🔐 Traçabilité Blockchain

Chaque transaction est scellée cryptographiquement :

```
Fingerprint  = SHA-256(champs_transaction)
Chain Hash   = SHA-256(fingerprint + hash_précédent)
Signature    = RSA-PSS(chain_hash, clé_privée)
QR Code      = encode(fingerprint) → vérification physique
Daily Anchor = SHA-256(tous les chain_hashes du jour)
```

Si une donnée est modifiée après validation → le hash change → fraude détectée.

---

## 📁 Structure du projet

```
trustnet/
├── data/
│   └── sample_transactions.csv   ← 50 transactions avec anomalies injectées
├── src/
│   ├── ingestion.py              ← Lecture CSV/Excel + validation
│   ├── features.py               ← Feature engineering
│   ├── model.py                  ← Isolation Forest
│   ├── rules.py                  ← Règles métier
│   ├── explainer.py              ← Moteur d'explication
│   ├── blockchain.py             ← Cryptographie + QR
│   └── pipeline.py               ← Orchestrateur
├── dashboard/
│   └── app.py                    ← Interface Streamlit
├── output/                       ← Résultats générés (gitignored)
├── run.py                        ← Point d'entrée CLI
├── requirements.txt
└── README.md
```

---

## 📊 Dashboard

Le dashboard Streamlit offre 3 vues :

**🔍 Recherche & Détail** — Recherchez par Transaction ID, client, pays ou catégorie. Cliquez sur une transaction pour voir son score, niveau de risque, et toutes les raisons de l'anomalie.

**🚨 Alertes Critiques** — Vue consolidée de toutes les transactions à risque élevé, triées par score décroissant.

**📊 Vue Globale** — Distribution des risques, transactions suspectes par pays, export CSV.

---

## 🗂️ Format du fichier d'entrée

| Colonne | Type | Exemple |
|---------|------|---------|
| Transaction_ID | string | TX001 |
| Customer | string | Samsung |
| Country | string | USA |
| Category | string | Electronics |
| Quantity | int | 12 |
| Value | float | 145000 |
| Weight | float | 420 |
| Customs_Code | string | 8471.30 |
| Payment_Terms | string | NET30 |
| Date | date | 2024-01-05 |
| Country_Origine | string | South Korea *(optionnel)* |

---

## 🛠️ Stack technique

| Composant | Technologie |
|-----------|-------------|
| Anomaly Detection | scikit-learn — IsolationForest |
| Business Rules | Python custom engine |
| Explainability | Z-score + frequency analysis |
| Blockchain | hashlib SHA-256 + cryptography RSA-PSS |
| Dashboard | Streamlit |
| QR Verification | qrcode |
| Data | pandas, numpy |

---

## 💡 Ce que j'ai appris

- Appliquer **Isolation Forest** à des données transactionnelles mixtes
- Concevoir un pipeline **hybride ML + règles métier** (comme les vrais systèmes AML)
- Générer des **explications humaines** lisibles par des analystes non-techniques
- Résoudre le **cold start problem** par un fallback sur profils globaux
- Implémenter la **traçabilité blockchain** sur un flux transactionnel réel

---

## 🌍 Contexte réel

Inspiré de **PortNet Maroc** — la plateforme nationale de dédouanement.  
La fraude douanière (sous-déclarations, fausses origines) coûte des milliards annuellement.  
TrustNet propose une couche de détection légère, explicable et vérifiable.

---

*Built by [Votre Nom] — Data Science & ML Engineering*
