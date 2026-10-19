"""Test the read-only audit against isolated synthetic legacy data."""
import sqlite3

from tools.audit_dossier_jaune import inspect_legacy_database


def test_audit_classifies_risks_without_changing_tables(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as db:
        db.executescript("""
        CREATE TABLE launches (
          id TEXT PRIMARY KEY, orli_ref TEXT, restricted BOOLEAN NOT NULL DEFAULT 0
        );
        CREATE TABLE folders (
          id TEXT PRIMARY KEY, launch_id TEXT, slug TEXT
        );
        CREATE TABLE documents (
          id TEXT PRIMARY KEY, folder_id TEXT
        );
        CREATE TABLE document_versions (
          id TEXT PRIMARY KEY, document_id TEXT
        );
        CREATE TABLE impact_alerts (
          id TEXT PRIMARY KEY, launch_id TEXT
        );
        INSERT INTO launches VALUES ('l1', NULL, 0), ('l2', 'ORLI-42', 1);
        INSERT INTO folders VALUES
          ('f1', 'l1', 'jaune'),
          ('f2', 'l2', 'bleu'),
          ('f3', 'l1', 'couleur-inconnue');
        INSERT INTO documents VALUES
          ('d1', 'f1'), ('d2', 'f2'), ('d3', 'f3');
        INSERT INTO document_versions VALUES ('v1', 'd1'), ('v2', 'd1'), ('v3', 'd2');
        INSERT INTO impact_alerts VALUES ('a1','l2');
        """)

    report = inspect_legacy_database(f"sqlite:///{path}")
    assert report["mode"] == "read_only_no_changes"
    assert report["counts"]["documents"] == 3
    assert report["counts"]["document_versions"] == 3
    assert report["documents_by_old_color"] == {
        "bleu": 1, "couleur-inconnue": 1, "jaune": 1
    }
    assert report["documents_without_launch_orli"] == 2
    assert report["documents_from_restricted_launches"] == 1
    assert report["unrecognized_color_documents"] == 1
    assert report["orphan_document_origins"] == 0
    assert report["other_tables_with_launch_id"]["impact_alerts"] == 1
    assert report["blocking_findings"]

    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 3
        assert db.execute("SELECT COUNT(*) FROM document_versions").fetchone()[0] == 3
        assert db.execute("SELECT restricted FROM launches WHERE id = 'l2'").fetchone()[0] == 1


def test_audit_missing_required_tables_is_non_destructive(tmp_path):
    path = tmp_path / "partial.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE launches (id TEXT PRIMARY KEY)")
        db.execute("INSERT INTO launches VALUES ('L')")
    report = inspect_legacy_database(f"sqlite:///{path}")
    assert report["blocking_findings"]
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM launches").fetchone()[0] == 1
