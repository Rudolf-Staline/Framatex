#!/usr/bin/env python3
"""Inventaire STRICTEMENT EN LECTURE SEULE de l'ancien modèle dossier-par-lancement.

Usage: DATABASE_URL='postgresql+psycopg://...' python tools/audit_dossier_jaune.py
       DATABASE_URL='sqlite:///chemin/jeu-test.db' python tools/audit_dossier_jaune.py

N'exécute AUCUNE migration. Ne liste pas de noms de clients ni de contenu de fichiers.
Un code retour 2 signale des anomalies à examiner avant une transition.
"""
from __future__ import annotations

import json
import os
import sys
from collections import OrderedDict
from sqlalchemy import create_engine, inspect, text


COLORS = {"jaune", "rose", "bleu", "vert"}
COUNTS = (
    "launches", "folders", "documents", "document_versions",
    "approval_runs", "approval_decisions", "orli_links",
    "launch_members", "audit_events", "client_publications",
)


def inspect_legacy_database(url: str) -> dict:
    engine = create_engine(url, future=True)
    try:
        with engine.connect() as connection:
            # PostgreSQL: mark the current transaction read only before inspecting.
            if engine.dialect.name == "postgresql":
                connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            inspector = inspect(connection)
            tables = set(inspector.get_table_names())

            def count(table: str) -> int | None:
                if table not in tables:
                    return None
                # Values come only from the fixed allow-list or inspector names.
                # Every SELECT result is an aggregate, never a document title.
                return int(connection.execute(text(
                    'SELECT COUNT(*) FROM "' + table.replace('"', '""') + '"'
                )).scalar_one())

            report = {
                "mode": "read_only_no_changes",
                "dialect": engine.dialect.name,
                "counts": OrderedDict((name, count(name)) for name in COUNTS),
                "documents_by_old_color": {},
                "documents_without_launch_orli": None,
                "documents_from_restricted_launches": None,
                "unrecognized_color_documents": None,
                "orphan_document_origins": None,
                "other_tables_with_launch_id": {},
                "blocking_findings": [],
                "cautions": [
                    "La présence ou l'absence d'ORLI ne prouve pas l'identité d'un document.",
                    "Une même valeur ORLI peut concerner plusieurs documents.",
                    "Aucun fichier du stockage objet n'est ouvert ou vérifié par cet inventaire.",
                    "Les permissions effectives par utilisateur doivent être testées séparément.",
                ],
            }

            required = {"launches", "folders", "documents", "document_versions"}
            missing = sorted(required - tables)
            if missing:
                report["blocking_findings"].append(
                    "Tables héritées absentes : " + ", ".join(missing)
                )
                return report

            slugs = connection.execute(text("""
                SELECT COALESCE(f.slug, '<sans-dossier>') AS slug,
                       COUNT(d.id) AS total
                FROM documents AS d
                LEFT JOIN folders AS f ON f.id = d.folder_id
                GROUP BY COALESCE(f.slug, '<sans-dossier>')
                ORDER BY slug
            """)).all()
            report["documents_by_old_color"] = {
                str(slug): int(total) for slug, total in slugs
            }
            unknown = sum(int(n) for slug, n in slugs if slug not in COLORS)
            report["unrecognized_color_documents"] = unknown
            if unknown:
                report["blocking_findings"].append(
                    f"{unknown} documents sans couleur reconnue : arbitrage obligatoire"
                )

            # Count broken linkage without exposing identifying data.
            report["orphan_document_origins"] = int(connection.execute(text("""
                SELECT COUNT(*) FROM documents d
                LEFT JOIN folders f ON f.id = d.folder_id
                LEFT JOIN launches l ON l.id = f.launch_id
                WHERE f.id IS NULL OR l.id IS NULL
            """)).scalar_one())
            if report["orphan_document_origins"]:
                report["blocking_findings"].append(
                    f"{report['orphan_document_origins']} documents à provenance incomplète"
                )

            launch_columns = {
                col["name"] for col in inspector.get_columns("launches")
            }
            if "orli_ref" in launch_columns:
                report["documents_without_launch_orli"] = int(
                    connection.execute(text("""
                        SELECT COUNT(*) FROM documents d
                        JOIN folders f ON f.id = d.folder_id
                        JOIN launches l ON l.id = f.launch_id
                        WHERE l.orli_ref IS NULL OR TRIM(l.orli_ref) = ''
                    """)).scalar_one()
                )
            if "restricted" in launch_columns:
                report["documents_from_restricted_launches"] = int(
                    connection.execute(text("""
                        SELECT COUNT(*) FROM documents d
                        JOIN folders f ON f.id = d.folder_id
                        JOIN launches l ON l.id = f.launch_id
                        WHERE l.restricted = :yes
                    """), {"yes": True}).scalar_one()
                )
                if report["documents_from_restricted_launches"]:
                    report["blocking_findings"].append(
                        "Des documents étaient restreints par lancement : "
                        "la politique de reprise des droits doit être validée"
                    )

            # Dependencies: list table names and row counts, not source records.
            for table in sorted(tables - {"launches", "folders", "documents"}):
                column_names = {
                    col["name"] for col in inspector.get_columns(table)
                }
                if "launch_id" in column_names:
                    report["other_tables_with_launch_id"][table] = count(table)
            return report
    finally:
        engine.dispose()


def main() -> int:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        print("DATABASE_URL manquante : aucune connexion ouverte", file=sys.stderr)
        return 3
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    try:
        report = inspect_legacy_database(url)
    except Exception as exc:
        # Do not echo connection URLs or credentials via an exception repr.
        print("Inventaire impossible ; vérifier le schéma et les droits de lecture",
              file=sys.stderr)
        return 3
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if report["blocking_findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
