"""
TrustNet — blockchain.py
-------------------------
Rôle : Sceller chaque transaction avec une empreinte cryptographique.

Comment ça fonctionne :
  1. Fingerprint SHA-256 : hash unique des données de la transaction
  2. Chain Hash          : hash du fingerprint + hash précédent (chaînage)
                           → si une transaction est modifiée, toute la chaîne casse
  3. Signature RSA       : la "banque" signe le chain hash avec sa clé privée
                           → prouve qui a validé la transaction
  4. QR Code             : encode le fingerprint pour vérification physique
  5. Daily Anchor        : hash global de toutes les transactions du jour
                           → preuve d'intégrité du lot journalier

Pourquoi c'est utile en commerce international :
  Les déclarations douanières doivent être inaltérables.
  Si quelqu'un modifie une valeur après validation, le hash change → fraude détectée.
"""

import hashlib
import json
import os
import qrcode
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding


# ── Génération des clés RSA (une seule fois par session) ──────────────────────
def generate_keys():
    """Génère une paire de clés RSA 2048 bits pour la session."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    return private_key, public_key


# Champs utilisés pour le fingerprint (on inclut les champs importants)
FINGERPRINT_FIELDS = [
    "Transaction_ID", "Customer", "Country", "Category",
    "Quantity", "Value", "Weight", "Unit_Value",
    "Customs_Code", "Payment_Terms", "Date", "Country_Origine"
]


def compute_fingerprint(row: dict) -> str:
    """
    Calcule l'empreinte SHA-256 d'une transaction.
    Le tri des clés (sort_keys=True) garantit que l'ordre n'influence pas le hash.
    """
    tx_data = {
        field: str(row.get(field, ""))
        for field in FINGERPRINT_FIELDS
        if field in row
    }
    serialized = json.dumps(tx_data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_chain_hash(fingerprint: str, previous_hash: str) -> str:
    """
    Chaîne le fingerprint avec le hash précédent.
    C'est le principe fondamental de la blockchain :
    chaque bloc contient une référence au bloc précédent.
    """
    combined = fingerprint + previous_hash
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def sign_hash(chain_hash: str, private_key) -> str:
    """
    Signe le chain hash avec la clé privée RSA (signature PSS).
    Retourne la signature en hexadécimal.
    """
    signature = private_key.sign(
        chain_hash.encode("utf-8"),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    return signature.hex()


def generate_qr(transaction_id: str, fingerprint: str, output_dir: str) -> str:
    """
    Génère un QR code contenant l'ID et le fingerprint.
    Sauvegarde l'image PNG dans output_dir.
    Retourne le chemin du fichier QR.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    qr_content = json.dumps({
        "transaction_id": transaction_id,
        "fingerprint": fingerprint,
        "system": "TrustNet"
    }, ensure_ascii=False)

    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=6, border=2)
    qr.add_data(qr_content)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    filepath = os.path.join(output_dir, f"qr_{transaction_id}.png")
    img.save(filepath)

    return filepath


def seal_transactions(df, output_dir: str = "output/qr_codes") -> tuple:
    """
    Scelle toutes les transactions du DataFrame.

    Pour chaque transaction :
      - Calcule fingerprint, chain hash, signature, QR

    Retourne (df_enrichi, anchor_hash, private_key, public_key)
    """
    import pandas as pd

    df = df.copy()
    private_key, public_key = generate_keys()

    fingerprints  = []
    chain_hashes  = []
    signatures    = []
    qr_paths      = []

    previous_hash = "TRUSTNET_GENESIS_BLOCK"

    for _, row in df.iterrows():
        row_dict = row.to_dict()

        fp = compute_fingerprint(row_dict)
        ch = compute_chain_hash(fp, previous_hash)
        sig = sign_hash(ch, private_key)
        qr = generate_qr(str(row_dict.get("Transaction_ID", "TX")), fp, output_dir)

        fingerprints.append(fp)
        chain_hashes.append(ch)
        signatures.append(sig)
        qr_paths.append(qr)

        previous_hash = ch  # Chaînage séquentiel

    df["Fingerprint_Hash"]  = fingerprints
    df["TrustChain_Hash"]   = chain_hashes
    df["Bank_Signature"]    = signatures
    df["QR_File"]           = qr_paths

    # Daily Anchor : hash de toutes les transactions combinées
    anchor = hashlib.sha256("".join(chain_hashes).encode()).hexdigest()

    print(f"✅ {len(df)} transactions scellées — Daily Anchor : {anchor[:16]}...")
    return df, anchor, private_key, public_key


def verify_transaction(row: dict, claimed_fingerprint: str) -> bool:
    """
    Vérifie qu'une transaction n'a pas été modifiée.
    Recalcule le fingerprint et compare avec celui stocké.
    """
    actual = compute_fingerprint(row)
    return actual == claimed_fingerprint
