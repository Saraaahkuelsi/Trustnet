"""
TrustNet — create_users.py
---------------------------
Script utilitaire pour créer ou modifier des utilisateurs.

Usage :
    python create_users.py

Ce script :
  1. Demande les infos d'un nouvel utilisateur
  2. Hashe le mot de passe avec bcrypt (sécurisé)
  3. Met à jour auth/users.json automatiquement

Pourquoi hasher les mots de passe ?
  Ne jamais stocker un mot de passe en clair.
  bcrypt est l'algorithme standard : même si quelqu'un vole le fichier,
  il ne peut pas retrouver le mot de passe original.
"""

import json
import os
import sys
import getpass

try:
    import bcrypt
except ImportError:
    print("❌ bcrypt non installé. Lance : python -m pip install bcrypt")
    sys.exit(1)

USERS_FILE = os.path.join("auth", "users.json")


def hash_password(password: str) -> str:
    """Hash un mot de passe avec bcrypt (12 rounds)."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode(), salt).decode()


def load_users() -> dict:
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_users(data: dict):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def list_users(data: dict):
    print("\n📋 Utilisateurs existants :")
    print("-" * 50)
    for u in data["users"]:
        status = "✅" if u["active"] else "❌"
        print(f"  {status} {u['username']:<15} {u['role']:<12} {u['email']}")
    print()


def add_user(data: dict):
    print("\n➕ Ajouter un nouvel utilisateur")
    print("-" * 40)

    username  = input("Username       : ").strip()
    full_name = input("Nom complet    : ").strip()
    email     = input("Email          : ").strip()

    print("Rôle disponibles : admin / analyste / auditeur")
    role = input("Rôle           : ").strip().lower()

    if role not in ["admin", "analyste", "auditeur"]:
        print("❌ Rôle invalide.")
        return

    password = getpass.getpass("Mot de passe   : ")
    confirm  = getpass.getpass("Confirmer      : ")

    if password != confirm:
        print("❌ Les mots de passe ne correspondent pas.")
        return

    # Vérifier que le username n'existe pas déjà
    existing = [u["username"] for u in data["users"]]
    if username in existing:
        print(f"❌ L'utilisateur '{username}' existe déjà.")
        return

    new_id = str(len(data["users"]) + 1)
    hashed = hash_password(password)

    new_user = {
        "id":            new_id,
        "username":      username,
        "email":         email,
        "password_hash": hashed,
        "role":          role,
        "full_name":     full_name,
        "active":        True
    }

    data["users"].append(new_user)
    save_users(data)
    print(f"\n✅ Utilisateur '{username}' ({role}) créé avec succès !")


def update_password(data: dict):
    print("\n🔑 Modifier le mot de passe")
    print("-" * 40)

    username = input("Username : ").strip()
    user = next((u for u in data["users"] if u["username"] == username), None)

    if not user:
        print(f"❌ Utilisateur '{username}' introuvable.")
        return

    password = getpass.getpass("Nouveau mot de passe : ")
    confirm  = getpass.getpass("Confirmer            : ")

    if password != confirm:
        print("❌ Les mots de passe ne correspondent pas.")
        return

    user["password_hash"] = hash_password(password)
    save_users(data)
    print(f"✅ Mot de passe de '{username}' mis à jour !")


def toggle_user(data: dict):
    print("\n🔄 Activer/Désactiver un utilisateur")
    print("-" * 40)

    username = input("Username : ").strip()
    user = next((u for u in data["users"] if u["username"] == username), None)

    if not user:
        print(f"❌ Utilisateur '{username}' introuvable.")
        return

    user["active"] = not user["active"]
    status = "activé" if user["active"] else "désactivé"
    save_users(data)
    print(f"✅ Utilisateur '{username}' {status} !")


def main():
    print("=" * 50)
    print("  🔒 TrustNet — Gestion des utilisateurs")
    print("=" * 50)

    if not os.path.exists(USERS_FILE):
        print(f"❌ Fichier introuvable : {USERS_FILE}")
        print("   Lance ce script depuis la racine du projet.")
        sys.exit(1)

    data = load_users()

    while True:
        list_users(data)
        print("Options :")
        print("  1. Ajouter un utilisateur")
        print("  2. Modifier un mot de passe")
        print("  3. Activer / Désactiver un utilisateur")
        print("  4. Quitter")

        choice = input("\nChoix : ").strip()

        if choice == "1":
            add_user(data)
        elif choice == "2":
            update_password(data)
        elif choice == "3":
            toggle_user(data)
        elif choice == "4":
            print("\n👋 Au revoir !")
            break
        else:
            print("❌ Choix invalide.")


if __name__ == "__main__":
    main()
