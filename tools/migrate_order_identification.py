"""Ajout non destructif de la fiche commande : python -m tools.migrate_order_identification --apply."""
import argparse
from sqlalchemy import inspect, text
from app.core import engine


def apply_to_connection(conn):
    if "launches" not in inspect(conn).get_table_names():
        raise RuntimeError("Initialisez Framatex avant la fiche commande")
    columns = {c["name"] for c in inspect(conn).get_columns("launches")}
    if "identification_json" not in columns:
        conn.execute(text("ALTER TABLE launches ADD COLUMN identification_json TEXT NOT NULL DEFAULT '{}'"))
    # No table, role, RLS policy, file, identifier or version is replaced.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    with engine.begin() as conn:
        if args.apply:
            apply_to_connection(conn)
            print("Fiche commande prête")
        else:
            columns = {c["name"] for c in inspect(conn).get_columns("launches")}
            print("Fiche commande prête" if "identification_json" in columns else "Colonne identification_json à ajouter")


if __name__ == "__main__":
    main()
