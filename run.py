"""
TrustNet — run.py
------------------
Point d'entrée principal pour exécuter le pipeline en ligne de commande.

Usage :
    python run.py                              # utilise le dataset exemple
    python run.py data/mon_fichier.csv        # fichier personnalisé
    python run.py data/mon_fichier.xlsx       # Excel aussi
    python run.py data/sample.csv --no-seal  # sans blockchain (plus rapide)
"""

import sys
import os

# S'assurer qu'on peut importer src/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.pipeline import run_pipeline


def main():
    # Fichier par défaut = dataset exemple fourni
    filepath = "data/sample_transactions.csv"
    seal = True

    # Arguments optionnels
    args = sys.argv[1:]
    for arg in args:
        if arg == "--no-seal":
            seal = False
        elif not arg.startswith("--"):
            filepath = arg

    if not os.path.exists(filepath):
        print(f"❌ Fichier introuvable : {filepath}")
        print("   Usage : python run.py [chemin/fichier.csv] [--no-seal]")
        sys.exit(1)

    # Lancer le pipeline
    df = run_pipeline(filepath, seal=seal)

    # Afficher un résumé dans le terminal
    print("\n📊 RÉSUMÉ DES RÉSULTATS :")
    print("-" * 40)

    for level in ["Risque Élevé 🔴", "Risque Moyen 🟠", "Risque Faible 🟢"]:
        subset = df[df["Risk_Level"] == level]
        print(f"  {level} : {len(subset)} transaction(s)")

    print("\n🔴 Transactions à risque élevé :")
    high = df[df["Risk_Level"] == "Risque Élevé 🔴"].sort_values("TrustNet_Score", ascending=False)
    if high.empty:
        print("  Aucune")
    else:
        for _, row in high.iterrows():
            reasons = row["Rule_Violations"] + row["Explanation_Detail"]
            reason_str = reasons[0] if reasons else "Anomalie statistique"
            print(f"  • {row['Transaction_ID']} | {row['Customer']} | Score: {row['TrustNet_Score']:.0f}/100")
            print(f"    → {reason_str}")

    print(f"\n✅ Résultats complets : output/trustnet_results.csv")
    if seal:
        print(f"🔐 QR codes générés   : output/qr_codes/")
    print(f"\n💡 Pour le dashboard : streamlit run dashboard/app.py\n")


if __name__ == "__main__":
    main()
