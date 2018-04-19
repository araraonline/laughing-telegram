import sqlite3

import click


@click.command()
@click.argument('tables', nargs=-1)
@click.argument('io-db', type=click.Path(exists=True))
def CLI(tables, io_db):
    """Drop a list of tables from the database

    This will delete the tables in a transaction, and if some table does not
    exist, it will just assume it is there and delete it anyway (but no error
    issued).

    Arguments:
        tables (array[string]): A list of tables to be deleted.

    Inputs:
        db (sqlite3): The database from which the tables will be deleted.
    """
    conn = sqlite3.connect(io_db)
    cursor = conn.cursor()
    for table in tables:
        q = "DROP TABLE IF EXISTS ?"
        cursor.execute(q, [table])
    # execute actions in a transaction
    conn.commit()
    cursor.close()
    conn.close()
