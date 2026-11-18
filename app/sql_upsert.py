"""Dialect-correct INSERT ... ON CONFLICT for SQLite and PostgreSQL."""
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert


def insert_for(db, model):
    name = db.bind.dialect.name
    if name == 'sqlite':
        return sqlite_insert(model)
    if name == 'postgresql':
        return pg_insert(model)
    raise RuntimeError(f'Upsert unsupported on database dialect: {name}')
