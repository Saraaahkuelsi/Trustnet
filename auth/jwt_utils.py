"""
TrustNet — auth/jwt_utils.py
-----------------------------
Rôle : Créer et vérifier les tokens JWT.

C'est quoi un JWT ?
  Un JWT (JSON Web Token) est une chaîne signée qui contient des infos
  sur l'utilisateur (id, rôle, expiration). Chaque page vérifie ce token
  avant d'afficher quoi que ce soit.
  
  Structure : header.payload.signature
  Exemple   : eyJ0...abc.eyJ1...xyz.SflK...def

  Si le token est expiré ou modifié → accès refusé automatiquement.
"""

import jwt
import datetime
import os

# Clé secrète pour signer les tokens — en production, mets ça dans .env
SECRET_KEY = os.environ.get("TRUSTNET_SECRET", "trustnet-secret-key-change-in-production")
ALGORITHM  = "HS256"
EXPIRATION_MINUTES = 30  # Token valide 30 minutes


def create_token(user_id: str, username: str, role: str, email: str) -> str:
    """
    Crée un token JWT signé pour un utilisateur connecté.
    
    Le token contient :
      - user_id   : identifiant unique
      - username  : nom d'utilisateur
      - role      : admin / analyste / auditeur
      - email     : pour affichage
      - exp       : date d'expiration (30 min)
      - iat       : date de création
    """
    payload = {
        "user_id":  user_id,
        "username": username,
        "role":     role,
        "email":    email,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=EXPIRATION_MINUTES),
        "iat": datetime.datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict | None:
    """
    Vérifie un token JWT.
    
    Retourne le payload (dict) si valide.
    Retourne None si expiré ou invalide.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token expiré
    except jwt.InvalidTokenError:
        return None  # Token invalide ou modifié
