"""
TrustNet — pages/analyste.py
-----------------------------
Dashboard réservé au rôle Analyste.

Accès :
  ✅ Toutes les transactions (recherche, détail)
  ✅ Alertes risque élevé et moyen
  ✅ Vue globale
  ✅ Vérification QR
  ❌ Export CSV (interdit)
  ❌ Gestion utilisateurs (interdit)
  ❌ Logs d'audit (interdit)
"""

import streamlit as st
import pandas as pd
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.audit_logs import log_action


def render(df_raw: pd.DataFrame, user: dict):
    df = df_raw.copy()
    df["Explanations_List"] = df["Explanation_Detail"].apply(lambda x: x if isinstance(x, list) else [])
    df["Violations_List"]   = df["Rule_Violations"].apply(lambda x: x if isinstance(x, list) else [])

    tabs = st.tabs([
        "🔍 Recherche & Détail",
        "🚨 Alertes",
        "📊 Vue Globale",
        "🔗 Vérification QR"
    ])

    with tabs[0]:
        _tab_recherche(df, user)

    with tabs[1]:
        _tab_alertes(df, user)

    with tabs[2]:
        _tab_globale(df)

    with tabs[3]:
        _tab_qr(df, user)


def _tab_recherche(df, user):
    cs, cf = st.columns([3, 1])
    with cs:
        search = st.text_input("🔍", placeholder="ID, client, pays, catégorie...", label_visibility="collapsed")
    with cf:
        rf = st.selectbox("", ["Tous", "Risque Élevé 🔴", "Risque Moyen 🟠", "Risque Faible 🟢"], label_visibility="collapsed")

    mask = pd.Series([True] * len(df))
    if search:
        s = search.lower()
        mask = (
            df["Transaction_ID"].str.lower().str.contains(s, na=False) |
            df["Customer"].str.lower().str.contains(s, na=False) |
            df["Country"].str.lower().str.contains(s, na=False) |
            df["Category"].str.lower().str.contains(s, na=False)
        )
    if rf != "Tous":
        mask = mask & (df["Risk_Level"] == rf)

    filtered = df[mask].reset_index(drop=True)
    st.caption(f"{len(filtered)} transaction(s)")

    cols = ["Transaction_ID", "Customer", "Country", "Category",
            "Quantity", "Value", "Weight", "Unit_Value", "TrustNet_Score", "Risk_Level"]
    st.dataframe(
        filtered[cols].style.background_gradient(subset=["TrustNet_Score"], cmap="RdYlGn_r"),
        use_container_width=True, hide_index=True
    )

    if not filtered.empty:
        st.subheader("🔎 Détail transaction")
        sel = st.selectbox("Transaction", filtered["Transaction_ID"].tolist(), label_visibility="collapsed")
        if sel:
            tx = df[df["Transaction_ID"] == sel].iloc[0]
            log_action(user["username"], user["role"], "VIEW_TRANSACTION", f"{sel} — {tx['Customer']}")

            color = "#FF4444" if "Élevé" in tx["Risk_Level"] else "#FF8C00" if "Moyen" in tx["Risk_Level"] else "#00C853"
            ci, ca = st.columns(2)

            with ci:
                st.markdown(f"**{sel}** — {tx['Customer']}")
                st.write(f"🌍 {tx['Country']} | 📦 {tx['Category']}")
                st.write(f"Qty: {tx['Quantity']} | Val: {tx['Value']:,.0f} | Poids: {tx['Weight']:,.0f} kg")
                st.write(f"Prix unit.: {tx['Unit_Value']:,.1f} | Paiement: {tx['Payment_Terms']}")
                if "Fingerprint_Hash" in tx.index and pd.notna(tx["Fingerprint_Hash"]):
                    st.code(f"SHA-256: {str(tx['Fingerprint_Hash'])[:32]}...", language=None)

            with ca:
                st.markdown(f"""
                <div style="background:#0D1220;border-left:4px solid {color};border-radius:8px;padding:16px;">
                    <div style="color:#888;font-size:11px;">SCORE TRUSTNET</div>
                    <div style="font-size:2.5em;font-weight:bold;color:{color}">
                        {tx['TrustNet_Score']:.0f}<span style="font-size:0.4em;color:#888">/100</span>
                    </div>
                    <div style="color:#E0E6FF;">{tx['Risk_Level']}</div>
                </div>
                """, unsafe_allow_html=True)

            all_r = tx["Violations_List"] + tx["Explanations_List"]
            if all_r:
                st.markdown("**📋 Raisons :**")
                for r in all_r:
                    st.markdown(f"- {r}")
            else:
                st.success("✅ Aucune anomalie détectée")

            # Pas d'export pour l'analyste
            st.info("💡 L'export CSV est réservé aux administrateurs.")


def _tab_alertes(df, user):
    high = df[df["Risk_Level"] == "Risque Élevé 🔴"].sort_values("TrustNet_Score", ascending=False)
    med  = df[df["Risk_Level"] == "Risque Moyen 🟠"].sort_values("TrustNet_Score", ascending=False)

    if high.empty and med.empty:
        st.success("✅ Aucune alerte")
        return

    for label, rows, emoji in [("Risque Élevé", high, "🔴"), ("Risque Moyen", med, "🟠")]:
        if not rows.empty:
            st.markdown(f"### {emoji} {label} ({len(rows)})")
            for _, row in rows.iterrows():
                all_r = row["Violations_List"] + row["Explanations_List"]
                with st.expander(f"{emoji} {row['Transaction_ID']} | {row['Customer']} | Score: {row['TrustNet_Score']:.0f}/100"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**{row['Country']}** | {row['Category']}")
                        st.write(f"Valeur: {row['Value']:,.0f} | Paiement: {row['Payment_Terms']}")
                    with c2:
                        st.write(f"Score ML: {row['ML_Score_Normalized']:.0f}/100")
                        st.write(f"Score Règles: {row['Rule_Score']*100:.0f}/100")
                    for r in all_r:
                        st.markdown(f"- {r}")


def _tab_globale(df):
    st.subheader("Distribution des risques")
    rc = df["Risk_Level"].value_counts().reset_index()
    rc.columns = ["Niveau", "Nombre"]
    st.bar_chart(rc.set_index("Niveau"))

    suspect = df[df["Risk_Level"] != "Risque Faible 🟢"]
    if not suspect.empty:
        st.subheader("Transactions suspectes par pays")
        bc = suspect.groupby("Country").size().reset_index(name="Suspectes")
        st.bar_chart(bc.set_index("Country"))


def _tab_qr(df, user):
    alerts = df[df["Risk_Level"].isin(["Risque Élevé 🔴", "Risque Moyen 🟠"])]
    if alerts.empty:
        st.info("Aucune transaction à vérifier.")
        return

    tx_id = st.selectbox("Transaction", alerts["Transaction_ID"].tolist())
    if tx_id:
        tx = df[df["Transaction_ID"] == tx_id].iloc[0]
        qp = str(tx.get("QR_File", ""))
        c1, c2 = st.columns([1, 2])
        with c1:
            if qp and os.path.exists(qp):
                st.image(qp, width=180)
            else:
                st.warning("QR non disponible.")
        with c2:
            st.write(f"**{tx_id}** — {tx['Customer']}")
            st.write(f"Risque: {tx['Risk_Level']}")
            if "Fingerprint_Hash" in tx.index and pd.notna(tx["Fingerprint_Hash"]):
                st.code(str(tx["Fingerprint_Hash"]), language=None)
