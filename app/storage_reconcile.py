"""Rebuild local quota accounting and report orphan blobs; never erase originals.

Stop application writers before comparing against the business database.
"""
import argparse
import json
import sqlite3
from pathlib import Path
from .storage_budget import reconcile


def references(database):
    names = set()
    with sqlite3.connect(f'file:{Path(database).resolve()}?mode=ro', uri=True) as db:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in ('document_versions', 'partner_submissions', 'partner_attachments', 'partner_administrative_documents'):
            if table in tables:
                names.update(r[0] for r in db.execute(f'SELECT disk_name FROM {table}'))
    return names


def main():
    from .core import DATA_DIR
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--storage', type=Path, default=DATA_DIR / 'files')
    parser.add_argument('--database', type=Path, default=DATA_DIR / 'framat.db')
    args = parser.parse_args()
    print(json.dumps(reconcile(args.storage, referenced=references(args.database)), sort_keys=True))


if __name__ == '__main__':
    main()
