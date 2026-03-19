"""
TrustNet — model.py
--------------------
Rôle : Entraîner Isolation Forest et scorer chaque transaction.

Comment fonctionne Isolation Forest ?
  L'idée est simple : une anomalie est facile à "isoler".
  L'algorithme construit des arbres de décision aléatoires.
  Une transaction normale nécessite beaucoup de coupures pour être isolée.
  Une transaction anormale (extrême) est isolée en peu de coupures.
  → Score bas = peu de coupures = anomalie probable

Pourquoi 200 arbres, contamination 5% ?
  - 200 arbres → résultats stables même sur petit dataset
  - 5% → environ 1 transaction sur 20 est considérée anormale
    (taux réaliste pour un fichier douanier)
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


def prepare_model_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prépare la matrice de features pour Isolation Forest.
    
    - Variables numériques : normalisées avec StandardScaler
    - Variables catégorielles : encodées en one-hot
    
    On ne met PAS Transaction_ID, Customer, Date → pas informatifs pour le ML.
    """
    # Features numériques
    numerical = ["Quantity", "Value", "Weight", "Unit_Value"]

    # Features catégorielles → one-hot encoding
    categorical = ["Country", "Category", "Payment_Terms"]

    X_num = df[numerical].copy()

    # Normalisation des numériques (important pour IF)
    scaler = StandardScaler()
    X_num_scaled = pd.DataFrame(
        scaler.fit_transform(X_num),
        columns=numerical,
        index=df.index
    )

    # One-hot encoding des catégorielles
    X_cat = pd.get_dummies(df[categorical], drop_first=False)

    # Concaténation
    X = pd.concat([X_num_scaled, X_cat], axis=1)

    return X, scaler


def train_and_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Entraîne Isolation Forest sur le dataset complet et retourne
    le DataFrame enrichi avec :
      - ML_Anomaly_Score : score brut IF entre -1 (anomalie) et +1 (normal)
      - ML_Score_Normalized : score normalisé entre 0 (normal) et 100 (anomalie)
      - ML_Is_Anomaly : booléen True si IF le classe comme anomalie
    """
    df = df.copy()

    X, scaler = prepare_model_features(df)

    # Entraînement du modèle
    model = IsolationForest(
        n_estimators=200,      # Nombre d'arbres — plus = plus stable
        contamination=0.05,    # 5% des transactions supposées anormales
        random_state=42,       # Reproductibilité
        n_jobs=-1              # Utiliser tous les CPU disponibles
    )
    model.fit(X)

    # Scoring
    # decision_function retourne un score entre ~-0.5 et ~+0.5
    # Valeurs négatives = plus suspect
    raw_scores = model.decision_function(X)
    predictions = model.predict(X)  # -1 = anomalie, +1 = normal

    # Normalisation : on inverse et scale entre 0 et 100
    # Score 0 = parfaitement normal, Score 100 = très suspect
    min_s, max_s = raw_scores.min(), raw_scores.max()
    if max_s > min_s:
        normalized = 100 * (1 - (raw_scores - min_s) / (max_s - min_s))
    else:
        normalized = np.zeros(len(raw_scores))

    df["ML_Anomaly_Score"] = raw_scores
    df["ML_Score_Normalized"] = normalized.round(1)
    df["ML_Is_Anomaly"] = predictions == -1

    print(f"✅ Isolation Forest entraîné : {df['ML_Is_Anomaly'].sum()} anomalies détectées / {len(df)}")

    return df, model
