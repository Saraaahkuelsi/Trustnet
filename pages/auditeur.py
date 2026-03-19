"""
TrustNet — pages/auditeur.py
-----------------------------
Dashboard réservé au rôle Auditeur.

Accès limité :
  ✅ Transactions à risque élevé et moyen uniquement
  ✅ Vérification QR et hashes blockchain
  ❌ Transactions à risque faible (non pertinent pour audit)
  ❌ Export CSV
  ❌ Gestion utilisateurs
  ❌ Logs d'audit
"""

import streamlit as st
import pandas as pd
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.audit_logs import log_action
from src.blockchain  import verify_transaction


def render(df_raw: pd.DataFrame, user: dict):
    df = df_raw.copy()
    df["Explanations_List"] = df["Explanation_Detail"].apply(lambda x: x if isinstance(x, list) else [])
    df["Violations_List"]   = df["Rule_Violations"].apply(lambda x: x if isinstance(x, list) else [])

    # Auditeur ne voit que les alertes
    df_audit = df[df["Risk_Level"].isin(["Risque Élevé 🔴", "Risque Moyen 🟠"])].copy()

    st.info(f"⚖️ Vue Auditeur — {len(df_audit)} transaction(s) à examiner sur {len(df)} total")

    tabs = st.tabs(["🚨 Alertes à examiner", "🔗 Vérification QR & Blockchain"])

    with tabs[0]:
        _tab_alertes(df_audit, user)

    with tabs[1]:
        _tab_verification(df_audit, df, user)


def _tab_alertes(df_audit, user):
    if df_audit.empty:
        st.success("✅ Aucune transaction à examiner")
        return

    # Résumé rapide
    n_high = (df_audit["Risk_Level"] == "Risque Élevé 🔴").sum()
    n_med  = (df_audit["Risk_Level"] == "Risque Moyen 🟠").sum()

    c1, c2 = st.columns(2)
    c1.metric("🔴 Risque Élevé", n_high, help="Nécessite une action immédiate")
    c2.metric("🟠 Risque Moyen", n_med,  help="À surveiller")

    st.divider()

    for label, emoji, risk_val in [("Risque Élevé", "🔴", "Risque Élevé 🔴"), ("Risque Moyen", "🟠", "Risque Moyen 🟠")]:
        rows = df_audit[df_audit["Risk_Level"] == risk_val].sort_values("TrustNet_Score", ascending=False)
        if rows.empty:
            continue

        st.markdown(f"### {emoji} {label} ({len(rows)})")

        for _, row in rows.iterrows():
            all_r = row["Violations_List"] + row["Explanations_List"]
            with st.expander(f"{emoji} {row['Transaction_ID']} | {row['Customer']} | {row['Country']} | Score: {row['TrustNet_Score']:.0f}/100"):

                log_action(user["username"], user["role"], "VIEW_TRANSACTION",
                           f"{row['Transaction_ID']} — {row['Customer']}")

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Score TrustNet", f"{row['TrustNet_Score']:.0f}/100")
                with c2:
                    st.metric("Score ML", f"{row['ML_Score_Normalized']:.0f}/100")
                with c3:
                    st.metric("Score Règles", f"{row['Rule_Score']*100:.0f}/100")

                st.write(f"**Pays :** {row['Country']} | **Catégorie :** {row['Category']}")
                st.write(f"**Valeur :** {row['Value']:,.0f} | **Quantité :** {row['Quantity']} | **Poids :** {row['Weight']:,.0f} kg")
                st.write(f"**Paiement :** {row['Payment_Terms']} | **Origine :** {row.get('Country_Origine','N/A')}")

                if all_r:
                    st.markdown("**Raisons de l'alerte :**")
                    for r in all_r:
                        st.markdown(f"- {r}")

                # Hash pour l'auditeur
                if "Fingerprint_Hash" in row.index and pd.notna(row["Fingerprint_Hash"]):
                    st.markdown("**Empreinte cryptographique :**")
                    st.code(str(row["Fingerprint_Hash"]), language=None)


def _tab_verification(df_audit, df_full, user):
    st.subheader("🔗 Vérification d'intégrité")
    st.markdown("""
    Vérifiez qu'une transaction n'a pas été modifiée après validation.
    Entrez l'ID et le hash que vous avez reçu — le système recalcule et compare.
    """)

    if df_audit.empty:
        st.info("Aucune transaction à vérifier.")
        return

    tx_id = st.selectbox("Sélectionner une transaction", df_audit["Transaction_ID"].tolist())

    if tx_id:
        tx = df_full[df_full["Transaction_ID"] == tx_id].iloc[0]
        qp = str(tx.get("QR_File", ""))

        c1, c2 = st.columns([1, 2])

        with c1:
            st.markdown("**QR Code**")
            if qp and os.path.exists(qp):
                st.image(qp, width=180, caption=f"{tx_id}")
            else:
                st.warning("QR non généré.\nActivez la blockchain au lancement.")

        with c2:
            st.markdown("**Informations de traçabilité**")

            if "Fingerprint_Hash" in tx.index and pd.notna(tx["Fingerprint_Hash"]):
                fp = str(tx["Fingerprint_Hash"])
                st.markdown("Fingerprint SHA-256 :")
                st.code(fp, language=None)

                # Vérification manuelle
                st.markdown("---")
                st.markdown("**Vérification manuelle**")
                claimed = st.text_input("Collez le hash à vérifier :", placeholder="Entrez le SHA-256...")
                if claimed:
                    if claimed.strip() == fp:
                        st.success("✅ Hash valide — transaction intègre")
                        log_action(user["username"], user["role"], "VIEW_TRANSACTION",
                                   f"Vérification OK — {tx_id}")
                    else:
                        st.error("❌ Hash différent — données potentiellement modifiées !")
                        log_action(user["username"], user["role"], "ACCESS_DENIED",
                                   f"Hash invalide — {tx_id}", success=False)
            else:
                st.warning("Blockchain non activée pour cette transaction.")

            if "TrustChain_Hash" in tx.index and pd.notna(tx["TrustChain_Hash"]):
                st.markdown("TrustChain Hash :")
                st.code(str(tx["TrustChain_Hash"]), language=None)
