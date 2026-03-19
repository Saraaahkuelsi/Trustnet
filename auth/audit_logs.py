"""
TrustNet — auth/audit_logs.py
------------------------------
Rôle : Enregistrer toutes les actions importantes dans un fichier de logs.

Pourquoi les audit logs sont importants :
  Dans un système de compliance douanière, il faut pouvoir répondre à :
  - "Qui a consulté la transaction TX035 ?"
  - "Quand est-ce que l'admin s'est connecté ?"
  - "Qui a exporté les données ?"
  
  Chaque action est horodatée et signée avec un hash SHA-256
  pour garantir que les logs n'ont pas été modifiés.

Format d'un log :
  {
    "timestamp": "2024-01-15T14:32:10",
    "user":      "admin",
    "role":      "admin",
    "action":    "VIEW_TRANSACTION",
    "detail":    "TX035 — FraudCo",
    "ip":        "127.0.0.1",
    "log_hash":  "sha256..."
  }
"""

import json
import hashlib
import datetime
import os
from pathlib import Path

# Fichier de logs
LOGS_DIR  = "output"
LOGS_FILE = os.path.join(LOGS_DIR, "audit_logs.json")

# Types d'actions trackées
ACTIONS = {
    "LOGIN_SUCCESS":      "Connexion réussie",
    "LOGIN_FAILED":       "Tentative de connexion échouée",
    "LOGOUT":             "Déconnexion",
    "2FA_SUCCESS":        "Code 2FA validé",
    "2FA_FAILED":         "Code 2FA incorrect",
    "VIEW_TRANSACTION":   "Consultation d'une transaction",
    "VIEW_DASHBOARD":     "Accès au dashboard",
    "EXPORT_CSV":         "Export CSV",
    "RUN_PIPELINE":       "Lancement de l'analyse",
    "ACCESS_DENIED":      "Accès refusé (permission insuffisante)",
}


def _load_logs() -> list:
    """Charge les logs existants depuis le fichier JSON."""
    if not os.path.exists(LOGS_FILE):
        return []
    try:
        with open(LOGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_logs(logs: list):
    """Sauvegarde les logs dans le fichier JSON."""
    Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)
    with open(LOGS_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


def _compute_log_hash(entry: dict) -> str:
    """
    Calcule un hash SHA-256 de l'entrée de log.
    Permet de détecter si un log a été modifié après coup.
    """
    data = json.dumps({
        k: v for k, v in entry.items() if k != "log_hash"
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]


def log_action(
    username: str,
    role: str,
    action: str,
    detail: str = "",
    success: bool = True
):
    """
    Enregistre une action dans les logs d'audit.

    Paramètres
    ----------
    username : str  — nom de l'utilisateur
    role     : str  — rôle (admin/analyste/auditeur)
    action   : str  — type d'action (voir ACTIONS)
    detail   : str  — détail optionnel (ex: Transaction_ID)
    success  : bool — l'action a-t-elle réussi ?
    """
    entry = {
        "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
        "user":      username,
        "role":      role,
        "action":    action,
        "label":     ACTIONS.get(action, action),
        "detail":    detail,
        "success":   success,
    }
    entry["log_hash"] = _compute_log_hash(entry)

    logs = _load_logs()
    logs.append(entry)
    _save_logs(logs)


def get_logs(
    username: str = None,
    action: str = None,
    limit: int = 100
) -> list:
    """
    Récupère les logs, avec filtres optionnels.

    Paramètres
    ----------
    username : filtrer par utilisateur
    action   : filtrer par type d'action
    limit    : nombre maximum de logs à retourner (les plus récents)
    """
    logs = _load_logs()

    if username:
        logs = [l for l in logs if l.get("user") == username]
    if action:
        logs = [l for l in logs if l.get("action") == action]

    # Retourner les plus récents en premier
    return list(reversed(logs))[:limit]


def verify_log_integrity(logs: list) -> dict:
    """
    Vérifie l'intégrité de chaque entrée de log.
    Retourne un rapport avec le nombre de logs valides/corrompus.
    """
    valid   = 0
    corrupt = 0
    corrupt_entries = []

    for entry in logs:
        stored_hash   = entry.get("log_hash", "")
        expected_hash = _compute_log_hash(entry)
        if stored_hash == expected_hash:
            valid += 1
        else:
            corrupt += 1
            corrupt_entries.append(entry.get("timestamp", "unknown"))

    return {
        "total":    len(logs),
        "valid":    valid,
        "corrupt":  corrupt,
        "corrupt_timestamps": corrupt_entries
    }
