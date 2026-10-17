"""python -m app.bootstrap_admin --email admin@exemple.local"""
import argparse
import getpass
from sqlalchemy import select
from .core import Base, engine, SessionLocal, hash_password
from .models import User, Role


def main():
    p = argparse.ArgumentParser(description="Créer le premier administrateur Framatex")
    p.add_argument("--email", required=True)
    p.add_argument("--name", default="Administrateur")
    args = p.parse_args()
    if "@" not in args.email:
        p.error("Email invalide")
    password = getpass.getpass("Mot de passe (12 caractères minimum) : ")
    confirmation = getpass.getpass("Confirmer le mot de passe : ")
    if password != confirmation:
        p.error("Les mots de passe ne correspondent pas")
    digest = hash_password(password)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == args.email.lower())):
            p.error("Cet email possède déjà un compte")
        role = db.scalar(select(Role).where(Role.name == "Administrateur"))
        if not role:
            role = Role(name="Administrateur")
            db.add(role)
        admin = User(email=args.email.lower(), name=args.name, password_hash=digest)
        admin.roles.append(role)
        db.add(admin)
        db.commit()
        print("Compte administrateur créé. Connexion :", args.email.lower())

if __name__ == "__main__": main()
