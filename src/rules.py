

"""
TrustNet — rules.py
--------------------
Rôle : Détecter les violations de règles métier que le ML ne peut pas voir.

Pourquoi des règles métier en plus du ML ?
  L'Isolation Forest détecte des anomalies STATISTIQUES.

  Mais certaines fraudes sont logiquement évidentes :
  - Une transaction vers un pays sous embargo → toujours suspecte
  - Une valeur déclarée de 100€ pour 200 armes → impossible
  - Paiement CASH pour une grosse transaction → signal d'alerte
  
  Ces règles sont les "garde-fous" que tout système de compliance réel possède.
  Elles ajoutent un score de risque fixe indépendant du ML.
"""

# ── Listes de référence ───────────────────────────────────────────────────────

# Pays sous embargo international (liste simplifiée pour démonstration)
EMBARGO_COUNTRIES = {
    "North Korea", "Iran", "Syria", "Cuba", "Russia",
    "Belarus", "Myanmar", "Sudan", "Venezuela"
}

# Catégories à haut risque nécessitant une vérification renforcée
HIGH_RISK_CATEGORIES = {
    "Weapons", "Pharmaceuticals", "Chemicals", "Nuclear", "Dual-Use"
}

# Combinaisons (pays, catégorie) automatiquement critiques
CRITICAL_COMBINATIONS = {
    ("North Korea", "Electronics"),
    ("Iran", "Chemicals"),
    ("Syria", "Weapons"),
    ("Russia", "Weapons"),
    ("Belarus", "Weapons"),
}

# Seuil de valeur au-dessus duquel CASH est suspect (en unité monétaire)
CASH_HIGH_VALUE_THRESHOLD = 50_000


# ── Fonction principale ───────────────────────────────────────────────────────

def apply_business_rules(row: dict) -> list:
    """
    Applique les règles métier sur une transaction.

    Paramètres
    ----------
    row : dict ou pd.Series
        Une transaction avec ses champs

    Retourne
    --------
    list de str — chaque string est une violation détectée
    """
    violations = []

    country  = str(row.get("Country", ""))
    category = str(row.get("Category", ""))
    value    = float(row.get("Value", 0))
    quantity = float(row.get("Quantity", 0))
    weight   = float(row.get("Weight", 0))
    payment  = str(row.get("Payment_Terms", ""))
    origine  = str(row.get("Country_Origine", ""))

    # ── Règle 1 : Pays sous embargo ──────────────────────────────────────
    if country in EMBARGO_COUNTRIES:
        violations.append(f"🚫 Pays sous embargo international : {country}")

    if origine in EMBARGO_COUNTRIES:
        violations.append(f"🚫 Pays d'origine sous embargo : {origine}")

    # ── Règle 2 : Combinaison critique (pays + catégorie) ────────────────
    if (country, category) in CRITICAL_COMBINATIONS:
        violations.append(
            f"🔴 Combinaison critique interdite : {country} × {category}"
        )

    # ── Règle 3 : Catégorie à haut risque ────────────────────────────────
    if category in HIGH_RISK_CATEGORIES:
        violations.append(f"⚠️ Catégorie à haut risque : {category}")

    # ── Règle 4 : Valeur nulle ou quasi-nulle ────────────────────────────
    if value == 0:
        violations.append("❌ Valeur déclarée = 0 (transaction invalide)")
    elif value < 100:
        violations.append(f"❌ Valeur déclarée anormalement basse : {value}")

    # ── Règle 5 : Quantité nulle ou suspecte ────────────────────────────
    if quantity == 0:
        violations.append("❌ Quantité = 0 (transaction invalide)")
    elif quantity > 500:
        violations.append(f"⚠️ Quantité extrêmement élevée : {quantity}")

    # ── Règle 6 : Poids nul ──────────────────────────────────────────────
    if weight == 0:
        violations.append("❌ Poids = 0 (déclaration incomplète)")

    # ── Règle 7 : CASH pour grosse transaction ───────────────────────────
    if payment.upper() == "CASH" and value > CASH_HIGH_VALUE_THRESHOLD:
        violations.append(
            f"💰 Paiement CASH pour une valeur élevée ({value:,.0f}) — risque blanchiment"
        )

    # ── Règle 8 : Ratio valeur/poids incohérent ──────────────────────────
    if weight > 0 and value > 0:
        ratio = value / weight
        if ratio < 0.5:
            violations.append(
                f"⚖️ Ratio valeur/poids très faible ({ratio:.2f}) — possible sous-déclaration"
            )

    return violations


def compute_rule_score(violations: list) -> float:
    """
    Convertit les violations en score de risque entre 0.0 et 1.0.
    
    Logique : chaque violation ajoute 0.25, plafonné à 1.0.
    Les violations critiques (embargo, combinaison interdite) ajoutent 0.5.
    """
    if not violations:
        return 0.0

    score = 0.0
    for v in violations:
        if "embargo" in v.lower() or "critique" in v.lower() or "invalide" in v.lower():
            score += 0.5
        else:
            score += 0.25

    return min(1.0, score)
