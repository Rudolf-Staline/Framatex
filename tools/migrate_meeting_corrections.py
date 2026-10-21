"""Additive migration: python -m tools.migrate_meeting_corrections --apply."""
import argparse
from sqlalchemy import inspect, text
from app.core import Base, engine
from app import models, document_comment_models  # noqa: F401


def apply_to_connection(conn):
    Base.metadata.tables['document_comments'].create(bind=conn, checkfirst=True)
    if 'comparison_mode' not in {c['name'] for c in inspect(conn).get_columns('cross_document_rules')}:
        conn.execute(text("ALTER TABLE cross_document_rules ADD COLUMN comparison_mode VARCHAR(32) NOT NULL DEFAULT 'equality'"))
    if conn.dialect.name == 'postgresql':
        conn.execute(text('ALTER TABLE public.document_comments ENABLE ROW LEVEL SECURITY'))
        conn.execute(text('REVOKE ALL ON TABLE public.document_comments FROM PUBLIC, anon, authenticated'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    with engine.begin() as conn:
        if args.apply:
            apply_to_connection(conn)
        print('Commentaires :', 'document_comments' in inspect(conn).get_table_names())
        print('Livraisons partielles :', 'comparison_mode' in {c['name'] for c in inspect(conn).get_columns('cross_document_rules')})


if __name__ == '__main__':
    main()
