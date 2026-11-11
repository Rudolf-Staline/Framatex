"""Add approval cycles without mutating any historical run or decision."""
from sqlalchemy import inspect
from sqlalchemy.schema import CreateTable
from .core import Base


def rebuild(conn,name):
    table=Base.metadata.tables[name]
    old={c['name'] for c in inspect(conn).get_columns(name)}
    columns=', '.join('"'+c.name+'"' for c in table.columns if c.name in old)
    temporary=name+'_phase3'
    ddl=str(CreateTable(table).compile(conn)).replace('CREATE TABLE '+name, 'CREATE TABLE '+temporary,1)
    conn.exec_driver_sql(ddl)
    conn.exec_driver_sql(f'INSERT INTO {temporary} ({columns}) SELECT {columns} FROM {name}')
    conn.exec_driver_sql(f'DROP TABLE {name}')
    conn.exec_driver_sql(f'ALTER TABLE {temporary} RENAME TO {name}')
    for index in table.indexes:index.create(conn,checkfirst=True)


def upgrade(conn):
    if 'cycle' not in {c['name'] for c in inspect(conn).get_columns('approval_runs')}:rebuild(conn,'approval_runs')
    if 'order_id' not in {c['name'] for c in inspect(conn).get_columns('internal_notifications')}:rebuild(conn,'internal_notifications')
