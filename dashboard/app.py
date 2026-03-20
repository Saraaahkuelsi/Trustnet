"""
TrustNet — dashboard/app.py
"""

from dotenv import load_dotenv
load_dotenv(dotenv_path="C:/Users/SARA/Desktop/Trusnet/.env")

import streamlit as st
import pandas as pd
import sys, os, json, datetime, tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.jwt_utils  import create_token, verify_token
from auth.email_2fa  import generate_2fa_code, send_2fa_email, is_code_valid
from auth.rbac       import can_access, get_role_info, filter_data_by_role
from src.pipeline    import run_pipeline

st.set_page_config(page_title="TrustNet", page_icon="🔒", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0A0E1A; }
    section[data-testid="stSidebar"] { background-color: #0D1220 !important; border-right: 1px solid #1A2540; }
    .stTextInput input { background: #0D1220 !important; color: #E0E6FF !important; border: 1px solid #1A2540 !important; }
    .stButton > button { background: #2563EB !important; color: white !important; border: none !important; border-radius: 8px !important; font-weight: 600 !important; }
    .stButton > button:hover { background: #1D4ED8 !important; }
    h1, h2, h3 { color: #E0E6FF !important; }
    p, label { color: #8090B0 !important; }
    .stDataFrame { background: #0D1220; }
    [data-testid="stAppViewContainer"] { background-color: #0A0E1A !important; }
    [data-testid="stHeader"] { background-color: #0A0E1A !important; }
</style>
""", unsafe_allow_html=True)


def load_users():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "auth", "users.json")
    with open(path) as f:
        return json.load(f)["users"]

def get_user_by_username(username):
    for u in load_users():
        if u["username"] == username and u["active"]:
            return u
    return None

def verify_password(plain, hashed):
    import bcrypt
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False

def get_current_user():
    token = st.session_state.get("jwt_token")
    if not token: return None
    payload = verify_token(token)
    if not payload:
        st.session_state.pop("jwt_token", None)
        return None
    return payload


def load_from_db():
    """Fonction commune pour charger les données depuis la base."""
    from src.database import get_all_transactions
    rows = get_all_transactions()
    if not rows:
        return None
    df_db = pd.DataFrame(rows)
    df_db = df_db.rename(columns={
        "transaction_id": "Transaction_ID",
        "customer":       "Customer",
        "country":        "Country",
        "category":       "Category",
        "quantity":       "Quantity",
        "value":          "Value",
        "weight":         "Weight",
        "unit_value":     "Unit_Value",
        "payment_terms":  "Payment_Terms",
        "date":           "Date",
        "trustnet_score": "TrustNet_Score",
        "risk_level":     "Risk_Level",
        "explanation":    "Explanation_Detail",
        "violations":     "Rule_Violations",
        "fingerprint":    "Fingerprint_Hash"
    })
    df_db["Explanation_Detail"] = df_db["Explanation_Detail"].apply(
        lambda x: x.split(" | ") if isinstance(x, str) and x else []
    )
    df_db["Rule_Violations"] = df_db["Rule_Violations"].apply(
        lambda x: x.split(" | ") if isinstance(x, str) and x else []
    )
    for col in ["ML_Score_Normalized", "Rule_Score"]:
        if col not in df_db.columns:
            df_db[col] = 0.0
    return df_db


# ── LOGIN ─────────────────────────────────────────────────────────────────────
def page_login():
    st.markdown("""
    <div style="text-align:center;padding:40px 0 20px 0;">
        <div style="font-size:48px;">🔒</div>
        <h1 style="color:#E0E6FF;margin:8px 0;">TRUSTNET</h1>
        <p style="color:#4A6090;letter-spacing:0.1em;font-size:0.85em;">Anomaly Detection · IMPORT/EXPORT</p>
    </div>""", unsafe_allow_html=True)

    _, col, _ = st.columns([1,2,1])
    with col:
        username = st.text_input("👤 Nom d'utilisateur", placeholder="User")
        password = st.text_input("🔑 Mot de passe", type="password", placeholder="Password")
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        if st.button("Se connecter →", use_container_width=True):
            if not username or not password:
                st.error("Remplissez tous les champs.")
                return

            if "login_attempts" not in st.session_state:
                st.session_state["login_attempts"] = 0

            if st.session_state["login_attempts"] >= 3:
                st.error("🔒 Compte bloqué — trop de tentatives. Relancez le dashboard.")
                return

            user = get_user_by_username(username)
            if not user:
                st.session_state["login_attempts"] += 1
                st.error(f"❌ Utilisateur introuvable. Tentative {st.session_state['login_attempts']}/3")
                return

            if not verify_password(password, user["password_hash"]):
                st.session_state["login_attempts"] += 1
                st.error(f"❌ Mot de passe incorrect. Tentative {st.session_state['login_attempts']}/3")
                return

            st.session_state["login_attempts"] = 0

            if user["role"] == "admin":
                code = generate_2fa_code()
                sent = send_2fa_email(user["email"], user["full_name"], code)
                if not sent:
                    st.error("❌ Impossible d'envoyer le code de vérification. Réessayez.")
                    return
                st.session_state.update({
                    "2fa_code": code,
                    "2fa_time": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
                    "2fa_user": user,
                    "2fa_pending": True
                })
                st.rerun()
            else:
                token = create_token(user["id"], user["username"], user["role"], user["email"])
                st.session_state["jwt_token"] = token
                st.rerun()

        st.markdown("""
        <div style="background:#0D1220;border:1px solid #1A2540;border-radius:8px;padding:12px;margin-top:12px;">
            <p style="color:#FF8C00;font-size:11px;margin:0 0 6px 0;">⚠️ Environnement de démonstration — données simulées</p>
            <p style="color:#4A6090;font-size:11px;margin:2px 0;">👑 <b style="color:#E0E6FF">admin</b> / trustnet2024 — accès complet + 2FA</p>
            <p style="color:#4A6090;font-size:11px;margin:2px 0;">🔍 <b style="color:#E0E6FF">analyste1</b> / trustnet2024 — consultation</p>
            <p style="color:#4A6090;font-size:11px;margin:2px 0;">⚖️ <b style="color:#E0E6FF">auditeur1</b> / trustnet2024 — alertes seulement</p>
        </div>""", unsafe_allow_html=True)


# ── 2FA ───────────────────────────────────────────────────────────────────────
def page_2fa():
    user = st.session_state.get("2fa_user", {})
    _, col, _ = st.columns([1,2,1])
    with col:
        st.markdown(f"""
        <div style="text-align:center;padding:40px 0 20px 0;">
            <div style="font-size:40px;">📧</div>
            <h2 style="color:#E0E6FF;">Vérification en 2 étapes</h2>
            <p style="color:#4A6090;font-size:12px;">Le code expire dans 5 minutes</p>
        </div>""", unsafe_allow_html=True)

        code_entered = st.text_input("Code à 6 chiffres", placeholder="000000", max_chars=6)
        ca, cb = st.columns(2)
        with ca:
            if st.button("✅ Vérifier", use_container_width=True):
                if is_code_valid(st.session_state.get("2fa_code"), st.session_state.get("2fa_time"), code_entered):
                    token = create_token(user["id"], user["username"], user["role"], user["email"])
                    st.session_state["jwt_token"] = token
                    st.session_state["2fa_pending"] = False
                    for k in ["2fa_code","2fa_time","2fa_user"]:
                        st.session_state.pop(k, None)
                    st.success("✅ Connexion réussie !")
                    st.rerun()
                else:
                    st.error("❌ Code incorrect ou expiré.")
        with cb:
            if st.button("← Retour", use_container_width=True):
                st.session_state["2fa_pending"] = False
                st.rerun()


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
def render_sidebar(user):
    ri = get_role_info(user["role"])
    with st.sidebar:
        st.markdown(f"<div style='padding:16px 0;'><div style='font-size:24px;font-weight:800;color:#E0E6FF;'>🔒 TRUSTNET</div><div style='font-size:10px;color:#4A6090;letter-spacing:0.1em;'>ANOMALY DETECTION</div></div>", unsafe_allow_html=True)
        st.divider()
        st.markdown(f"""
        <div style="background:#0A0E1A;border:1px solid #1A2540;border-radius:8px;padding:12px;margin-bottom:16px;">
            <div style="color:#E0E6FF;font-weight:600;">{ri['icon']} {user['username']}</div>
            <div style="font-size:11px;color:#4A6090;">{user['email']}</div>
            <div style="margin-top:6px;"><span style="background:{ri['color']}22;color:{ri['color']};border:1px solid {ri['color']}44;padding:2px 8px;border-radius:10px;font-size:11px;">{ri['label']}</span></div>
        </div>""", unsafe_allow_html=True)

        source = None
        seal = True
        if can_access(user["role"], "view_all_transactions"):
            st.subheader("📂 Données")
            source = st.radio("Source", ["📁 Uploader un fichier", "🗄️ Historique"], label_visibility="collapsed")
            seal = st.toggle("🔐 Blockchain", value=True)

        st.divider()
        if st.button("🚪 Déconnexion", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
    return source, seal


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    if st.session_state.get("2fa_pending"):
        page_2fa(); return

    user = get_current_user()
    if not user:
        page_login(); return

    source, seal = render_sidebar(user)

    filepath = None

    # Auditeur — charge automatiquement l'historique depuis la base
    if user["role"] == "auditeur":
        if "results" not in st.session_state:
            df_db = load_from_db()
            if df_db is not None:
                st.session_state["results"] = df_db

    elif source == "📁 Uploader un fichier":
        up = st.file_uploader("Fichier CSV/Excel", type=["csv","xlsx"])
        if up:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(up.name)[1]) as tmp:
                tmp.write(up.read())
                filepath = tmp.name

    elif source == "🗄️ Historique":
        df_db = load_from_db()
        if df_db is not None:
            st.session_state["results"] = df_db
            st.success(f"✅ {len(df_db)} transactions chargées depuis la base")
        else:
            st.warning("⚠️ Aucune transaction dans la base. Lancez d'abord une analyse.")

    if filepath and st.sidebar.button("🚀 Lancer l'analyse", type="primary", use_container_width=True):
        with st.spinner("Analyse en cours..."):
            try:
                df = run_pipeline(filepath, seal=seal)
                st.session_state["results"] = df
            except Exception as e:
                st.error(f"Erreur : {e}")

    df = st.session_state.get("results")
    if df is not None:
        role = user["role"]
        if role == "admin":
            from pages.admin import render
        elif role == "analyste":
            from pages.analyste import render
        else:
            from pages.auditeur import render
        render(df, user)
    else:
        st.markdown(f"<div style='text-align:center;padding:80px 0;'><div style='font-size:48px;'>🔒</div><h2 style='color:#E0E6FF;'>Bienvenue, {user['username']}</h2><p style='color:#4A6090;'>Cliquez sur <b>Lancer l'analyse</b> dans le menu à gauche.</p></div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()