"""
TrustNet — features.py
-----------------------
Rôle : Transformer les données brutes en features utilisables par le modèle.

Ce module construit 4 choses :
  1. Unit_Value         → valeur par unité (détecte sous-facturation)
  2. Profils globaux    → moyenne/écart-type par pays × catégorie
  3. Profils importateurs → comportement typique de chaque client
  4. Tables de fréquences → rareté de chaque valeur catégorielle

Pourquoi c'est important :
  Le même poids de 5000kg est normal pour de la Machinerie mais suspect
  pour de l'Électronique. Les features contextuelles capturent ça.
"""

import pandas as pd
import numpy as np

MIN_HISTORY = 5  # Seuil : si < 5 transactions → cold start


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute Unit_Value et Importer_Profile_ID au DataFrame."""
    df = df.copy()

    # Prix unitaire — indicateur clé de sous/sur-facturation
    df["Unit_Value"] = (df["Value"] / df["Quantity"].replace(0, np.nan)).fillna(0)

    # Identifier les importateurs avec peu d'historique
    counts = df["Customer"].value_counts()
    df["Importer_Profile_ID"] = df.apply(
        lambda row: row["Customer"]
        if counts.get(row["Customer"], 0) >= MIN_HISTORY
        else f"{row['Country']}_{row['Category']}",
        axis=1
    )
    df["Has_History"] = df["Customer"].map(counts) >= MIN_HISTORY

    return df


def build_global_profiles(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construit les profils statistiques par (Country, Category).
    Retourne un DataFrame avec moyenne et écart-type pour chaque combinaison.
    Ces profils servent de référence pour les importateurs sans historique.
    """
    profil = df.groupby(["Country", "Category"]).agg(
        Quantity_mean=("Quantity", "mean"), Quantity_std=("Quantity", "std"),
        Value_mean=("Value", "mean"),    Value_std=("Value", "std"),
        Weight_mean=("Weight", "mean"),  Weight_std=("Weight", "std"),
        Unit_Value_mean=("Unit_Value", "mean"), Unit_Value_std=("Unit_Value", "std"),
        Transaction_count=("Transaction_ID", "count")
    ).reset_index()

    # Remplacer les NaN (groupe avec 1 seule valeur) par 0
    for col in profil.columns:
        if col.endswith("_std"):
            profil[col] = profil[col].fillna(0)

    return profil


def build_importer_profiles(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construit les profils comportementaux par importateur.
    Uniquement pour ceux avec >= MIN_HISTORY transactions.
    """
    qualified = df[df["Has_History"]]
    if qualified.empty:
        return pd.DataFrame()

    profil = qualified.groupby("Customer").agg(
        Quantity_mean=("Quantity", "mean"), Quantity_std=("Quantity", "std"),
        Value_mean=("Value", "mean"),       Value_std=("Value", "std"),
        Weight_mean=("Weight", "mean"),     Weight_std=("Weight", "std"),
        Unit_Value_mean=("Unit_Value", "mean"), Unit_Value_std=("Unit_Value", "std"),
        Transaction_count=("Transaction_ID", "count")
    ).reset_index()

    for col in profil.columns:
        if col.endswith("_std"):
            profil[col] = profil[col].fillna(0)

    return profil


def build_frequency_tables(df: pd.DataFrame) -> dict:
    """
    Calcule la fréquence relative de chaque valeur catégorielle.
    Une valeur rare = potentiellement suspecte.

    Retourne un dict :
      { "Country": {"USA": 0.15, "Germany": 0.12, ...}, ... }
    """
    tables = {}
    for col in ["Country", "Category", "Customs_Code", "Payment_Terms", "Country_Origine"]:
        if col in df.columns:
            tables[col] = df[col].value_counts(normalize=True).to_dict()

    # Fréquences des combinaisons Country × Category × Country_Origine
    combo = df.groupby(["Country", "Category", "Country_Origine"]).size()
    combo = (combo / len(df)).reset_index(name="freq")
    tables["freq_combination"] = combo

    return tables
