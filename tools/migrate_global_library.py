"""Transactional and idempotent *additive* global document backfill.

No legacy IDs, folders, versions, files, ACLs or launch metadata are deleted.
Production PostgreSQL: require separately verified database + object backups.
CLI default is a read-only dry run. Test it on a restored copy first.

python -m tools.migrate_global_library
python -m tools.migrate_global_library --apply --backup-confirmed
"""
from __future__ import annotations

import argparse
import json
import os

from sqlalchemy import create_engine, func, insert, inspect, select
from sqlalchemy.engine import Connection, Engine

from app.models import Document, Folder, Launch
from app.global_library_models import GlobalFolder, GlobalDocumentEntry, GlobalLibraryConfig

COLORS = (("jaune", "Technique"), ("rose", "Réception"),
          ("bleu", "Douane"), ("vert", "Facturation"))


def count_invalid(conn: Connection) -> tuple[int, int]:
    document_count = conn.scalar(select(func.count(Document.id))) or 0
    records = conn.execute(
        select(Document.id, Folder.slug, Launch.id)
        .select_from(Document)
        .outerjoin(Folder, Document.folder_id == Folder.id)
        .outerjoin(Launch, Folder.launch_id == Launch.id)
    )
    valid = sum(
        1 for _id, slug, launch_id in records
        if slug in {color for color, _ in COLORS} and launch_id is not None
    )
    return document_count, document_count - valid


def apply_to_connection(conn: Connection) -> dict:
    """Perform the backfill on an existing DB transaction."""
    required = {"launches", "folders", "documents", "document_versions"}
    if not required.issubset(set(inspect(conn).get_table_names())):
        raise RuntimeError("Schéma ancien incomplet : migration annulée")
    total, invalid = count_invalid(conn)
    if invalid:
        raise RuntimeError(f"{invalid} documents sans rubrique ou lancement valide")
    GlobalFolder.__table__.create(bind=conn, checkfirst=True)
    GlobalDocumentEntry.__table__.create(bind=conn, checkfirst=True)
    GlobalLibraryConfig.__table__.create(bind=conn, checkfirst=True)
    present = set(conn.scalars(select(GlobalFolder.slug)).all())
    for slug, label in COLORS:
        if slug not in present:
            conn.execute(insert(GlobalFolder).values(slug=slug, label=label))
    # A migration replay never rewrites a user-corrected ORLI reference.
    existing = set(conn.scalars(select(GlobalDocumentEntry.document_id)).all())
    added = 0
    rows = conn.execute(
        select(Document.id, Folder.slug, Folder.id, Launch.id, Launch.orli_ref)
        .join(Folder, Document.folder_id == Folder.id)
        .join(Launch, Folder.launch_id == Launch.id)
    )
    for document_id, slug, folder_id, launch_id, orli in rows:
        if document_id in existing:
            continue
        conn.execute(insert(GlobalDocumentEntry).values(
            document_id=document_id,
            folder_slug=slug,
            orli_ref=(orli.strip() or None) if orli else None,
            orli_overridden=False,
            legacy_folder_id=folder_id,
            legacy_launch_id=launch_id,
        ))
        added += 1
    final = conn.scalar(select(func.count(GlobalDocumentEntry.document_id))) or 0
    if final != total:
        raise RuntimeError(f"Contrôle nombre documents : {total} != {final}")
    if conn.dialect.name == "postgresql":
        # Supabase exposes public to the Data API. The legacy Framatex schema
        # enforces RLS even when ORM access uses a privileged server role.
        # Do the same for every new global table in the migration transaction.
        from sqlalchemy import text
        for table_name in ("global_folders", "global_document_entries", "global_library_config"):
            conn.execute(text(f'ALTER TABLE public.{table_name} ENABLE ROW LEVEL SECURITY'))
            conn.execute(text(f'REVOKE ALL ON TABLE public.{table_name} FROM PUBLIC'))
            for role in ("anon", "authenticated"):
                present = conn.scalar(text("SELECT 1 FROM pg_roles WHERE rolname=:name"), {"name": role})
                if present:
                    conn.execute(text(f'REVOKE ALL ON TABLE public.{table_name} FROM {role}'))
    return {
        "source_documents": total,
        "indexed_documents": final,
        "added": added,
        "rubriques": len(COLORS),
        "legacy_documents_unchanged": True,
        "storage_files_unchanged": True,
    }



def apply_upgrade(engine: Engine) -> dict:
    with engine.begin() as conn:
        return apply_to_connection(conn)

def run() -> int:
    parser = argparse.ArgumentParser(description="Migration additive Dossier Jaune global")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-confirmed", action="store_true")
    args = parser.parse_args()
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        parser.error("DATABASE_URL obligatoire ; aucune connexion établie")
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    if args.apply and not args.backup_confirmed:
        parser.error("--backup-confirmed est requis après restauration vérifiée")
    engine = create_engine(url, future=True)
    try:
        if args.apply:
            result = apply_upgrade(engine)
        else:
            with engine.connect() as conn:
                total, invalid = count_invalid(conn)
                result = {"dry_run": True, "source_documents": total,
                          "invalid_origins": invalid, "writes": 0}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if not result.get("invalid_origins") else 2
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(run())
