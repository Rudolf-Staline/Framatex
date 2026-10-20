"""Ajout transactionnel des fiches métier et des attentes documentaires.

python -m tools.migrate_document_intelligence --apply
Ne modifie ni les documents existants, ni les règles, ni les rôles existants.
"""
from __future__ import annotations
import argparse
from sqlalchemy import inspect, text
from app.core import engine
from app.experience_models import ExperienceRecord, DocumentExpectation

TABLES = (ExperienceRecord.__table__, DocumentExpectation.__table__)


def apply_to_connection(conn):
    existing = set(inspect(conn).get_table_names())
    if not {"users", "global_folders", "document_versions"}.issubset(existing):
        raise RuntimeError("Initialisez le Dossier Jaune unique avant la mémoire métier")
    for table in TABLES:
        table.create(conn, checkfirst=True)
        if conn.dialect.name == "postgresql":
            name = conn.dialect.identifier_preparer.quote(table.name)
            conn.execute(text(f'ALTER TABLE public.{name} ENABLE ROW LEVEL SECURITY'))
            conn.execute(text(f'REVOKE ALL ON TABLE public.{name} FROM PUBLIC, anon, authenticated'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    with engine.begin() as conn:
        existing = set(inspect(conn).get_table_names())
        if args.apply:
            apply_to_connection(conn)
            print("Mémoire métier et attentes initialisées")
        else:
            print("Tables à ajouter :", ", ".join(t.name for t in TABLES if t.name not in existing) or "aucune")


if __name__ == "__main__":
    main()
