"""Explicit one-time bootstrap for an EMPTY dedicated Supabase demo project.

Never run this against Horizon, ECC Laundry or any existing application DB.
No migrations from existing SQLite installations are attempted here.
"""
from __future__ import annotations

import argparse
import os
from sqlalchemy import inspect, text
from .core import Base, engine

# Imports all SQLAlchemy models, without importing the SQLite migrator.
from . import models, completeness_models, workflow_models, quality_models  # noqa: F401
from . import intake_models, spec_models, mail_models, impact_sim_models  # noqa: F401
from . import orli_models, material_models, approval_models, sharing_models, pilot_models  # noqa: F401
from . import global_library_models  # noqa: F401
from . import experience_models  # noqa: F401

REQUIRED = {"users", "roles", "launches", "folders", "documents", "document_versions", "audit_events",
            "global_folders", "global_document_entries", "global_library_config",
            "experience_records", "document_expectations"}


def assert_ready():
    if engine.dialect.name != "postgresql":
        raise RuntimeError("La verification Supabase demande PostgreSQL")
    with engine.connect() as conn:
        existing = set(inspect(conn).get_table_names(schema="public"))
        missing = REQUIRED - existing
        if missing:
            raise RuntimeError("Base demo non initialisee : executer explicitement python -m app.demo_postgres init")
        # Public is an exposed Supabase Data API schema by default.
        rows = conn.execute(text("""SELECT c.relname, c.relrowsecurity FROM pg_class c
            JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relkind='r'""")).all()
        insecure = sorted(name for name, enabled in rows if name in Base.metadata.tables and not enabled)
        if insecure:
            raise RuntimeError(f"RLS requis pour les tables Framatex : {', '.join(insecure)}")
        colors = set(conn.execute(text("SELECT slug FROM public.global_folders")).scalars())
        if colors != {"jaune", "rose", "bleu", "vert"}:
            raise RuntimeError("Indexation du Dossier Jaune non initialisee : migration V2 requise")



def bootstrap():
    if engine.dialect.name != "postgresql":
        raise RuntimeError("Le bootstrap distant exige une connexion PostgreSQL")
    if os.getenv("FRAMATEX_CONFIRM_EMPTY_DEMO_DB") != "I_CONFIRM_NEW_EMPTY_FRAMATEX_DATABASE":
        raise RuntimeError("Refus : confirmer explicitement une nouvelle base vide via FRAMATEX_CONFIRM_EMPTY_DEMO_DB")
    with engine.begin() as conn:
        inspector = inspect(conn)
        existing = set(inspector.get_table_names(schema="public"))
        if existing:
            raise RuntimeError(f"Refus de modifier une base contenant deja des tables : {sorted(existing)}")
        Base.metadata.create_all(bind=conn)
        quoted = conn.dialect.identifier_preparer.quote
        for table in Base.metadata.sorted_tables:
            if table.schema not in (None, "public"):
                raise RuntimeError("Seules les tables du schema public dedie sont autorisees")
            name = quoted(table.name)
            conn.execute(text(f'ALTER TABLE public.{name} ENABLE ROW LEVEL SECURITY'))
            conn.execute(text(f'REVOKE ALL ON TABLE public.{name} FROM PUBLIC, anon, authenticated'))
    assert_ready()
    print("Schema Framatex demo initialise, RLS active et acces Data API non autorises.")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("command",choices=("status","init"),default="status",nargs="?")
    args=parser.parse_args()
    bootstrap() if args.command=="init" else assert_ready()

if __name__=="__main__":main()
