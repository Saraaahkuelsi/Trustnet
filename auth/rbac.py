"""
TrustNet — auth/rbac.py
------------------------
Rôle : Définir et vérifier les permissions par rôle (RBAC).

RBAC = Role-Based Access Control
  Chaque rôle a des permissions précises.
  Chaque page appelle can_access() avant d'afficher quoi que ce soit.
  Si l'utilisateur n'a pas la permission → redirigé vers login.
"""

# ── Définition des permissions par rôle ───────────────────────────────────────
PERMISSIONS = {
    "admin": {
        "view_all_transactions":   True,
        "view_high_risk":          True,
        "view_medium_risk":        True,
        "view_low_risk":           True,
        "export_csv":              True,
        "manage_users":            True,
        "view_audit_logs":         True,
        "verify_qr":               True,
        "view_blockchain":         True,
    },
    "analyste": {
        "view_all_transactions":   True,
        "view_high_risk":          True,
        "view_medium_risk":        True,
        "view_low_risk":           True,
        "export_csv":              False,  # Pas d'export
        "manage_users":            False,
        "view_audit_logs":         False,
        "verify_qr":               True,
        "view_blockchain":         False,
    },
    "auditeur": {
        "view_all_transactions":   False,  # Seulement les alertes
        "view_high_risk":          True,
        "view_medium_risk":        True,
        "view_low_risk":           False,
        "export_csv":              False,
        "manage_users":            False,
        "view_audit_logs":         False,
        "verify_qr":               True,   # Peut vérifier les QR
        "view_blockchain":         True,   # Peut voir les hashes
    }
}

# Description lisible de chaque rôle pour l'UI
ROLE_LABELS = {
    "admin":    {"label": "Administrateur", "icon": "👑", "color": "#2563EB"},
    "analyste": {"label": "Analyste",        "icon": "🔍", "color": "#00C853"},
    "auditeur": {"label": "Auditeur",        "icon": "⚖️",  "color": "#FF8C00"},
}


def can_access(role: str, permission: str) -> bool:
    """
    Vérifie si un rôle a une permission donnée.
    
    Exemple :
        can_access("analyste", "export_csv")  → False
        can_access("admin", "manage_users")   → True
    """
    role_perms = PERMISSIONS.get(role, {})
    return role_perms.get(permission, False)


def get_role_info(role: str) -> dict:
    """Retourne les infos d'affichage pour un rôle."""
    return ROLE_LABELS.get(role, {"label": role, "icon": "👤", "color": "#888"})


def filter_data_by_role(df, role: str):
    """
    Filtre le DataFrame selon le rôle :
      - admin    → tout
      - analyste → tout
      - auditeur → seulement risque élevé et moyen
    """
    if role == "auditeur":
        return df[df["Risk_Level"].isin(["Risque Élevé 🔴", "Risque Moyen 🟠"])]
    return df
