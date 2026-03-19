"""
TrustNet — ingestion.py
------------------------
Rôle : Lire un fichier CSV ou Excel, valider les colonnes, nettoyer les données.

Pourquoi ce fichier existe :
  Dans un vrai projet douanier, les données arrivent de sources externes
  (exports ERP, fichiers déclaratifs, API bancaires). Ce module isole toute
  la logique de lecture pour que le reste du code soit indépendant de la source.
"""

import pandas as pd
from pathlib import Path

REQUIRED_COLUMNS = [
    "Transaction_ID", "Customer", "Country", "Category",
    "Quantity", "Value", "Weight", "Customs_Code", "Payment_Terms", "Date"
]
NUMERIC_COLUMNS = ["Quantity", "Value", "Weight"]


def load_file(filepath: str) -> pd.DataFrame:
    """
    Charge un fichier CSV ou Excel et retourne un DataFrame propre.
    Lève ValueError si colonnes manquantes ou format invalide.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {filepath}")

    ext = path.suffix.lower()
    if ext == ".csv":
        df = pd.read_csv(filepath)
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(filepath)
    else:
        raise ValueError(f"Format non supporté : {ext}. Utilisez .csv ou .xlsx")

    print(f"✅ Fichier chargé : {path.name} ({len(df)} transactions)")

    # Validation des colonnes obligatoires
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes : {missing}")

    # Nettoyage
    df.columns = df.columns.str.strip()
    df = df.dropna(how="all")

    for col in ["Transaction_ID", "Customer", "Country", "Category", "Payment_Terms", "Customs_Code"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).clip(lower=0)

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    if "Country_Origine" not in df.columns:
        df["Country_Origine"] = "Unknown"
    else:
        df["Country_Origine"] = df["Country_Origine"].fillna("Unknown")

    df = df.reset_index(drop=True)
    print(f"✅ Nettoyage terminé : {len(df)} transactions valides")
    return df
