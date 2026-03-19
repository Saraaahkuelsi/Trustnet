"""
TrustNet — pages/admin.py
--------------------------
Dashboard réservé au rôle Admin.

Accès complet :
  - Toutes les transactions (recherche, détail, export)
  - Toutes les alertes
  - Vue globale + statistiques
  - Gestion des utilisateurs
  - Logs d'audit
  - Vérification QR + blockchain
"""

import streamlit as st
import pandas as pd
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.rbac       import can_access
from auth.audit_logs import log_action, get_logs, verify_log_integrity


def render(df_raw: pd.DataFrame, user: dict):
    """Point d'entrée principal de la page admin."""

    df = df_raw.copy()
    df["Explanations_List"] = df["Explanation_Detail"].apply(lambda x: x if isinstance(x, list) else [])
    df["Violations_List"]   = df["Rule_Violations"].apply(lambda x: x if isinstance(x, list) else [])

    tabs = st.tabs([
        "🔍 Recherche & Détail",
        "🚨 Alertes Critiques",
        "📊 Vue Globale",
        "👥 Utilisateurs",
        "📋 Logs d'Audit",
        "🔗 Vérification QR"
    ])

    # ── TAB 1 : Recherche ─────────────────────────────────────────────
    with tabs[0]:
        _tab_recherche(df, user)

    # ── TAB 2 : Alertes ───────────────────────────────────────────────
    with tabs[1]:
        _tab_alertes(df, user)

    # ── TAB 3 : Vue Globale ───────────────────────────────────────────
    with tabs[2]:
        _tab_globale(df, user)

    # ── TAB 4 : Utilisateurs ──────────────────────────────────────────
    with tabs[3]:
        try:
            _tab_users(user)
        except Exception as e:
             st.error(f"Erreur : {e}")

    # ── TAB 5 : Logs d'Audit ──────────────────────────────────────────
    with tabs[4]:
        _tab_audit(user)

    # ── TAB 6 : QR ────────────────────────────────────────────────────
    with tabs[5]:
        _tab_qr(df, user)


def _tab_recherche(df, user):
    cs, cf = st.columns([3, 1])
    with cs:
        search = st.text_input("🔍", placeholder="ID, client, pays, catégorie...", label_visibility="collapsed")
    with cf:
        rf = st.selectbox("Filtre ", ["Tous", "Risque Élevé 🔴", "Risque Moyen 🟠", "Risque Faible 🟢"], label_visibility="collapsed")

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
                st.write(f"Origine: {tx['Country_Origine']}")
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
                    <div style="margin-top:8px;color:#888;font-size:12px;">
                        ML: {tx['ML_Score_Normalized']:.0f} | Règles: {tx['Rule_Score']*100:.0f}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            all_r = tx["Violations_List"] + tx["Explanations_List"]
            if all_r:
                st.markdown("**📋 Raisons :**")
                for r in all_r:
                    st.markdown(f"- {r}")
            else:
                st.success("✅ Aucune anomalie détectée")

            # Export (admin peut toujours exporter)
            row_df = df[df["Transaction_ID"] == sel].copy()
            row_df["Explanation_Detail"] = row_df["Explanations_List"].apply(lambda x: " | ".join(x))
            csv = row_df[cols + ["Explanation_Detail"]].to_csv(index=False)
            if st.download_button("⬇️ Exporter cette transaction", csv, f"{sel}.csv", "text/csv"):
                log_action(user["username"], user["role"], "EXPORT_CSV", f"Transaction {sel}")


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
                    if all_r:
                        for r in all_r:
                            st.markdown(f"- {r}")


def _tab_globale(df, user):
    st.subheader("Distribution des risques")
    rc = df["Risk_Level"].value_counts().reset_index()
    rc.columns = ["Niveau", "Nombre"]
    st.bar_chart(rc.set_index("Niveau"))

    suspect = df[df["Risk_Level"] != "Risque Faible 🟢"]
    if not suspect.empty:
        st.subheader("Transactions suspectes par pays")
        bc = suspect.groupby("Country").size().reset_index(name="Suspectes")
        st.bar_chart(bc.set_index("Country"))

        st.subheader("Par catégorie")
        cc = suspect.groupby("Category").size().reset_index(name="Suspectes")
        st.bar_chart(cc.set_index("Category"))

    st.subheader("📥 Export complet")
    ex = df.copy()
    ex["Explanation_Detail"] = ex["Explanations_List"].apply(lambda x: " | ".join(x))
    ex["Rule_Violations"]    = ex["Violations_List"].apply(lambda x: " | ".join(x))
    csv = ex[["Transaction_ID", "Customer", "Country", "Category",
              "TrustNet_Score", "Risk_Level", "Explanation_Detail", "Rule_Violations"]
             ].to_csv(index=False, encoding="utf-8-sig")

    if st.download_button("⬇️ Exporter tout (CSV)", csv, "trustnet_results.csv", "text/csv", use_container_width=True):
        log_action(user["username"], user["role"], "EXPORT_CSV", "Export complet")


def _tab_users(user=None):
    st.write("test")
    import json
    users_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "auth", "users.json")
    with open(users_path) as f:
        users = json.load(f)["users"]

    st.subheader(f"👥 Utilisateurs ({len(users)})")
    udf = pd.DataFrame([{
        "Username": u["username"],
        "Nom":      u["full_name"],
        "Email":    u["email"],
        "Rôle":     u["role"],
        "Statut":   "✅ Actif" if u["active"] else "❌ Inactif"
    } for u in users])
    st.dataframe(udf, use_container_width=True, hide_index=True)
    st.info("💡 Pour modifier les utilisateurs, éditez auth/users.json puis relancez.")


def _tab_audit(user):
    st.subheader("📋 Logs d'audit")

    col_f, col_l = st.columns([2, 1])
    with col_f:
        filter_user = st.text_input("Filtrer par utilisateur", placeholder="Tous")
    with col_l:
        limit = st.selectbox("Nombre de logs", [20, 50, 100], index=0)

    logs = get_logs(username=filter_user if filter_user else None, limit=limit)

    if not logs:
        st.info("Aucun log disponible.")
        return

    # Vérification d'intégrité
    integrity = verify_log_integrity(logs)
    if integrity["corrupt"] > 0:
        st.error(f"⚠️ {integrity['corrupt']} log(s) corrompu(s) détecté(s) !")
    else:
        st.success(f"✅ Intégrité des logs vérifiée ({integrity['valid']} entrées valides)")

    logs_df = pd.DataFrame(logs)[["timestamp", "user", "role", "label", "detail", "success"]]
    logs_df.columns = ["Horodatage", "Utilisateur", "Rôle", "Action", "Détail", "Succès"]
    logs_df["Succès"] = logs_df["Succès"].map({True: "✅", False: "❌"})
    st.dataframe(logs_df, use_container_width=True, hide_index=True)


def _tab_qr(df, user):
    alerts = df[df["Risk_Level"].isin(["Risque Élevé 🔴", "Risque Moyen 🟠"])]
    if alerts.empty:
        st.info("Aucune transaction à vérifier.")
        return

    tx_id = st.selectbox("Transaction à vérifier", alerts["Transaction_ID"].tolist())
    if tx_id:
        tx = df[df["Transaction_ID"] == tx_id].iloc[0]
        qp = str(tx.get("QR_File", ""))

        c1, c2 = st.columns([1, 2])
        with c1:
            if qp and os.path.exists(qp):
                st.image(qp, width=200, caption=f"QR — {tx_id}")
            else:
                st.warning("QR non disponible.")
        with c2:
            st.write(f"**Transaction :** {tx_id}")
            st.write(f"**Client :** {tx['Customer']}")
            st.write(f"**Risque :** {tx['Risk_Level']}")
            st.write(f"**Score :** {tx['TrustNet_Score']:.0f}/100")
            if "Fingerprint_Hash" in tx.index and pd.notna(tx["Fingerprint_Hash"]):
                st.markdown("**Fingerprint SHA-256 :**")
                st.code(str(tx["Fingerprint_Hash"]), language=None)
            if "TrustChain_Hash" in tx.index and pd.notna(tx["TrustChain_Hash"]):
                st.markdown("**TrustChain Hash :**")
                st.code(str(tx["TrustChain_Hash"]), language=None)
