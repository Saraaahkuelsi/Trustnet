"""
TrustNet — explainer.py
------------------------
Rôle : Expliquer POURQUOI une transaction est suspecte, en langage humain.

Un score seul ne suffit pas pour un analyste douanier.
Ce module génère des raisons précises basées sur :
  1. Z-score numérique   → écart à la moyenne en nombre d'écarts-types
  2. Rareté catégorielle → valeur peu fréquente dans le dataset
  3. Contexte            → comparaison au profil importateur OU au profil global
  4. Cold start          → pas d'historique disponible

Exemple de sortie :
  ["Weight est extrêmement élevé (4.2σ) vs profil Japan/Machinery",
   "Combinaison rare : Kenya/Pharmaceuticals (0.3% du dataset)",
   "Prix unitaire anormalement élevé vs comportement typique de LVMH"]
"""

import pandas as pd
import numpy as np

# Seuil de z-score pour déclencher une explication
Z_THRESHOLD = 2.5

# Seuil de fréquence sous lequel une valeur est "rare"
FREQ_RARE = 0.01
FREQ_VERY_RARE = 0.005


def _zscore_explanation(col: str, value: float, mean: float, std: float, context: str = "") -> str | None:
    """Retourne une explication si la valeur dépasse le seuil Z."""
    if std == 0 or pd.isna(std) or pd.isna(mean):
        return None
    z = (value - mean) / std
    suffix = f" ({context})" if context else ""
    if z > Z_THRESHOLD:
        return f"{col} anormalement élevé ({z:.1f}σ){suffix}"
    elif z < -Z_THRESHOLD:
        return f"{col} anormalement faible ({abs(z):.1f}σ){suffix}"
    return None


def _rarity_explanation(feature: str, value: str, freq_table: dict) -> str | None:
    """Retourne une explication si la valeur est rare dans le dataset."""
    p = freq_table.get(str(value), 0)
    if p < FREQ_VERY_RARE:
        return f"{feature} '{value}' extrêmement rare dans le dataset ({p*100:.2f}%)"
    elif p < FREQ_RARE:
        return f"{feature} '{value}' rare dans le dataset ({p*100:.2f}%)"
    return None


def explain_transaction(
    row: pd.Series,
    global_profiles: pd.DataFrame,
    importer_profiles: pd.DataFrame,
    freq_tables: dict
) -> list:
    """
    Génère la liste complète des raisons d'anomalie pour une transaction.

    Logique de routage :
      → Si l'importateur a >= 5 transactions : utilise son profil individuel
      → Sinon (cold start) : utilise le profil global pays × catégorie
    """
    reasons = []

    customer = row.get("Customer", "")
    country  = row.get("Country", "")
    category = row.get("Category", "")

    cols_to_check = ["Quantity", "Value", "Weight", "Unit_Value"]

    # ── CAS 1 : Profil importateur disponible ──────────────────────────
    imp_row = importer_profiles[importer_profiles["Customer"] == customer]

    if not imp_row.empty:
        imp = imp_row.iloc[0]
        for col in cols_to_check:
            mean_col = f"{col}_mean"
            std_col  = f"{col}_std"
            if mean_col in imp.index and std_col in imp.index:
                msg = _zscore_explanation(
                    col, row[col], imp[mean_col], imp[std_col],
                    context=f"vs profil historique de {customer}"
                )
                if msg:
                    reasons.append(msg)

    # ── CAS 2 : Cold start → profil global ────────────────────────────
    else:
        reasons.append(f"❄️ Cold Start : aucun historique pour '{customer}' → profil global utilisé")

        prof_row = global_profiles[
            (global_profiles["Country"] == country) &
            (global_profiles["Category"] == category)
        ]

        if prof_row.empty:
            reasons.append(f"⚠️ Aucun profil global pour {country}/{category}")
        else:
            prof = prof_row.iloc[0]
            for col in cols_to_check:
                mean_col = f"{col}_mean"
                std_col  = f"{col}_std"
                if mean_col in prof.index:
                    msg = _zscore_explanation(
                        col, row[col], prof[mean_col], prof[std_col],
                        context=f"vs baseline {country}/{category}"
                    )
                    if msg:
                        reasons.append(msg)

    # ── Rareté catégorielle ────────────────────────────────────────────
    for feature in ["Country", "Category", "Payment_Terms", "Country_Origine"]:
        if feature in freq_tables and feature in row.index:
            msg = _rarity_explanation(feature, row[feature], freq_tables[feature])
            if msg:
                reasons.append(msg)

    # ── Combinaison rare Country × Category × Country_Origine ─────────
    freq_comb = freq_tables.get("freq_combination", pd.DataFrame())
    if not freq_comb.empty and "Country_Origine" in row.index:
        subset = freq_comb[
            (freq_comb["Country"] == country) &
            (freq_comb["Category"] == category) &
            (freq_comb["Country_Origine"] == row["Country_Origine"])
        ]
        freq_val = subset["freq"].values[0] if not subset.empty else 0
        if freq_val < FREQ_RARE:
            reasons.append(
                f"🌍 Combinaison rare : {country}/{category}/{row['Country_Origine']} "
                f"({freq_val*100:.2f}% du dataset)"
            )

    return reasons


def compute_final_score(
    ml_score: float,
    rule_score: float,
    n_explanations: int
) -> float:
    """
    Score final TrustNet = combinaison pondérée de 3 signaux :
      - ML score (Isolation Forest)     → 50% du poids
      - Rule score (règles métier)       → 35% du poids
      - Explanations score (nb raisons)  → 15% du poids

    Retourne un score entre 0 (normal) et 100 (très suspect).
    """
    expl_score = min(1.0, n_explanations / 5)
    combined = (0.50 * (ml_score / 100)) + (0.35 * rule_score) + (0.15 * expl_score)
    return round(min(100.0, combined * 100), 1)


def assign_risk_level(final_score: float) -> str:
    """Convertit le score final en niveau de risque lisible."""
    if final_score >= 60:
        return "Risque Élevé 🔴"
    elif final_score >= 30:
        return "Risque Moyen 🟠"
    else:
        return "Risque Faible 🟢"
