"""
TrustNet — pipeline.py
-----------------------
Rôle : Orchestrer toutes les étapes dans l'ordre correct.

C'est le chef d'orchestre : il appelle chaque module dans le bon ordre
et retourne un DataFrame final avec TOUTES les colonnes enrichies.

Tu peux appeler run_pipeline() depuis run.py ou depuis le dashboard Streamlit.
"""

import pandas as pd
import sys
import os

# Permet l'import depuis le dossier parent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ingestion  import load_file
from src.features   import build_features, build_global_profiles, build_importer_profiles, build_frequency_tables
from src.model      import train_and_score
from src.rules      import apply_business_rules, compute_rule_score
from src.explainer  import explain_transaction, compute_final_score, assign_risk_level
from src.blockchain import seal_transactions
from src.database import init_database, save_transaction


def run_pipeline(filepath: str, seal: bool = True, qr_dir: str = "output/qr_codes") -> pd.DataFrame:
    """
    Exécute le pipeline TrustNet complet sur un fichier.

    Étapes :
      1. Ingestion      → lecture et nettoyage
      2. Features       → Unit_Value, profils, fréquences
      3. ML Scoring     → Isolation Forest
      4. Règles métier  → violations légales/logiques
      5. Explication    → raisons humaines
      6. Score final    → combinaison ML + règles + explications
      7. Blockchain     → scellement cryptographique (optionnel)
      8. Export CSV     → sauvegarde du résultat

    Paramètres
    ----------
    filepath : str   — chemin vers le fichier CSV ou Excel
    seal     : bool  — activer le scellement blockchain (False = plus rapide)
    qr_dir   : str   — dossier de sortie des QR codes

    Retourne
    --------
    pd.DataFrame avec toutes les colonnes enrichies
    """

    print("\n" + "="*55)
    print("  🔒 TRUSTNET — Pipeline de détection d'anomalies")
    print("="*55)

    # ── ÉTAPE 1 : Ingestion ───────────────────────────────────────────
    print("\n📂 Étape 1 : Chargement du fichier...")
    df = load_file(filepath)

    # ── ÉTAPE 2 : Feature Engineering ────────────────────────────────
    print("\n⚙️  Étape 2 : Construction des features...")
    df = build_features(df)
    global_profiles   = build_global_profiles(df)
    importer_profiles = build_importer_profiles(df)
    freq_tables       = build_frequency_tables(df)
    print(f"   → {len(global_profiles)} profils globaux construits")
    print(f"   → {len(importer_profiles)} profils importateurs construits")

    # ── ÉTAPE 3 : Scoring ML ─────────────────────────────────────────
    print("\n🤖 Étape 3 : Scoring Isolation Forest...")
    df, model = train_and_score(df)

    # ── ÉTAPE 4 : Règles métier ───────────────────────────────────────
    print("\n📋 Étape 4 : Application des règles métier...")
    df["Rule_Violations"] = df.apply(
        lambda row: apply_business_rules(row.to_dict()), axis=1
    )
    df["Rule_Score"] = df["Rule_Violations"].apply(compute_rule_score)
    n_violations = (df["Rule_Score"] > 0).sum()
    print(f"   → {n_violations} transactions avec violations de règles")

    # ── ÉTAPE 5 : Explications ────────────────────────────────────────
    print("\n💬 Étape 5 : Génération des explications...")
    df["Explanation_Detail"] = df.apply(
        lambda row: explain_transaction(row, global_profiles, importer_profiles, freq_tables),
        axis=1
    )

    # ── ÉTAPE 6 : Score final et niveau de risque ─────────────────────
    print("\n📊 Étape 6 : Calcul du score final TrustNet...")
    df["TrustNet_Score"] = df.apply(
        lambda row: compute_final_score(
            ml_score       = row["ML_Score_Normalized"],
            rule_score     = row["Rule_Score"],
            n_explanations = len(row["Explanation_Detail"])
        ),
        axis=1
    )
    df["Risk_Level"] = df["TrustNet_Score"].apply(assign_risk_level)

    # Résumé des niveaux de risque
    counts = df["Risk_Level"].value_counts()
    for level, count in counts.items():
        print(f"   → {level} : {count} transactions")

    # ── ÉTAPE 7 : Blockchain (optionnel) ──────────────────────────────
    if seal:
        print("\n🔐 Étape 7 : Scellement blockchain...")
        df, anchor, priv_key, pub_key = seal_transactions(df, qr_dir)
        df.attrs["daily_anchor"] = anchor
    else:
        print("\n⏭️  Étape 7 : Scellement désactivé (seal=False)")

    # ── ÉTAPE 8 : Export ──────────────────────────────────────────────
    print("\n💾 Étape 8 : Export des résultats...")
    os.makedirs("output", exist_ok=True)
    output_path = "output/trustnet_results.csv"

    # Sérialiser les listes en string pour CSV
    export_df = df.copy()
    export_df["Explanation_Detail"] = export_df["Explanation_Detail"].apply(
        lambda x: " | ".join(x) if isinstance(x, list) else str(x)
    )
    export_df["Rule_Violations"] = export_df["Rule_Violations"].apply(
        lambda x: " | ".join(x) if isinstance(x, list) else str(x)
    )

    # Exclure les colonnes lourdes pour l'export
    cols_to_drop = [c for c in ["ML_Anomaly_Score", "Bank_Signature", "QR_File"] if c in export_df.columns]
    export_df.drop(columns=cols_to_drop).to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"   → Résultats sauvegardés : {output_path}")



# Initialiser la base de données si elle n'existe pas
    init_database()

# Sauvegarder chaque transaction dans la base
    print("\n💾 Sauvegarde dans la base de données...")
    for _, row in df.iterrows():
        save_transaction(row.to_dict())
    print(f"   → {len(df)} transactions sauvegardées dans trustnet.db")

    print("\n" + "="*55)
    print("  ✅ Pipeline terminé avec succès")
    print("="*55 + "\n")

    return df
