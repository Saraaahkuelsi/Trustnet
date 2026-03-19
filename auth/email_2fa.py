"""
TrustNet — auth/email_2fa.py
-----------------------------
Rôle : Générer et envoyer un code 2FA par email via Gmail.

Comment ça marche :
  1. L'utilisateur entre son mot de passe correct
  2. On génère un code à 6 chiffres aléatoire
  3. On l'envoie à son email via Gmail SMTP
  4. Le code est stocké en session avec une expiration de 5 minutes
  5. L'utilisateur saisit le code → accès accordé
"""

import smtplib
import random
import string
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

# ── Configuration Gmail ────────────────────────────────────────────────────
# Variables mis dans .env

GMAIL_ADDRESS      = os.environ.get("TRUSTNET_GMAIL")
GMAIL_APP_PASSWORD = os.environ.get("TRUSTNET_GMAIL_PWD")


CODE_EXPIRY_MINUTES = 5


def generate_2fa_code() -> str:
    """Génère un code numérique à 6 chiffres."""
    return "".join(random.choices(string.digits, k=6))


def send_2fa_email(to_email: str, username: str, code: str) -> bool:
    """
    Envoie le code 2FA par email via Gmail SMTP.
    
    Paramètres
    ----------
    to_email : str  — email du destinataire
    username : str  — nom d'utilisateur (pour personnaliser le message)
    code     : str  — code à 6 chiffres
    
    Retourne True si envoi réussi, False sinon.
    """
    subject = "🔒 TrustNet — Votre code de vérification"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto;">
        <div style="background: #0A0E1A; padding: 24px; border-radius: 10px;">
            <h2 style="color: #2563EB; margin: 0;">🔒 TrustNet</h2>
            <p style="color: #888; font-size: 12px;">Détection d'anomalies — Import/Export</p>
        </div>
        <div style="padding: 24px; background: #f9f9f9; border-radius: 0 0 10px 10px;">
            <p>Bonjour <strong>{username}</strong>,</p>
            <p>Voici votre code de vérification :</p>
            <div style="background: #0A0E1A; color: #2563EB; font-size: 32px; 
                        font-weight: bold; text-align: center; padding: 20px; 
                        border-radius: 8px; letter-spacing: 8px;">
                {code}
            </div>
            <p style="color: #888; font-size: 12px; margin-top: 16px;">
                ⏱️ Ce code expire dans <strong>{CODE_EXPIRY_MINUTES} minutes</strong>.<br>
                Si vous n'avez pas demandé ce code, ignorez cet email.
            </p>
        </div>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"❌ Erreur envoi email 2FA : {e}")
        return False


def is_code_valid(stored_code: str, stored_time: datetime.datetime,
                  entered_code: str) -> bool:
    """
    Vérifie que le code entré est correct et non expiré.
    """
    now = datetime.datetime.utcnow()
    elapsed = (now - stored_time).total_seconds() / 60  # en minutes

    if elapsed > CODE_EXPIRY_MINUTES:
        return False  # Code expiré

    return entered_code.strip() == stored_code
