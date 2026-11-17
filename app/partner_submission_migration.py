"""Preserve historical supplier transmissions while admitting staff-recorded sources."""
from sqlalchemy import inspect


def upgrade(conn):
    columns = {c['name']: c for c in inspect(conn).get_columns('partner_submissions')}
    if {'received_by','received_via','received_note'}.issubset(columns) and columns['account_id']['nullable']:
        return
    # Foreign keys are disabled by the central migrator for its entire transaction.
    # Rebuild under the same name without renaming the old table (which would
    # otherwise retarget referencing foreign keys on modern SQLite).
    from .partner_models import PartnerSubmission
    from sqlalchemy.schema import CreateTable
    ddl = str(CreateTable(PartnerSubmission.__table__).compile(conn))
    conn.exec_driver_sql(ddl.replace('CREATE TABLE partner_submissions', 'CREATE TABLE partner_submissions_received'))
    original = [name for name in columns if name in PartnerSubmission.__table__.columns]
    quoted = ','.join('"'+name+'"' for name in original)
    conn.exec_driver_sql(f'INSERT INTO partner_submissions_received ({quoted}) SELECT {quoted} FROM partner_submissions')
    conn.exec_driver_sql('DROP TABLE partner_submissions')
    conn.exec_driver_sql('ALTER TABLE partner_submissions_received RENAME TO partner_submissions')
    for index in PartnerSubmission.__table__.indexes:
        index.create(conn, checkfirst=True)
