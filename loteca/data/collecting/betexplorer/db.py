import sqlite3
import click


def save_leagues_to_db(db_loc, leagues):
    conn = sqlite3.connect(db_loc)
    c = conn.cursor()
    leagues = [(league['category'], league['name'], league['year'], league['url'], league['scraped'], league['complete']) for league in leagues]
    c.executemany("""
        INSERT OR IGNORE
        INTO leagues
        VALUES(?,?,?,?,?,?);""", leagues)
    conn.commit()
    conn.close()


@click.group()
def group():
    pass

@group.command()
@click.argument('location', type=click.Path(writable=True))
def create_db(location):
    conn = sqlite3.connect(location)
    conn.close()

@group.command()
@click.argument('db_loc', type=click.Path(exists=True))
def create_leagues_table(db_loc):
    conn = sqlite3.connect(db_loc)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS leagues (
            category text NOT NULL,
            name text NOT NULL,
            year text NOT NULL,
            url text NOT NULL,
            scraped INTEGER,
            complete INTEGER,
            PRIMARY KEY(category, name, year)
            );""")
    conn.commit()
    conn.close()

@group.command()
@click.argument('db_loc', type=click.Path(exists=True))
def create_basicmatches_table(db_loc):
    conn = sqlite3.connection(db_loc)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS basicmatches (
            id text PRIMARY KEY,
            league text NOT NULL,

            teamH text NOT NULL,
            teamA text NOT NULL,
            date text NOT NULL,

            score text,
            scoremod text,
            
            FOREIGN KEY(league) REFERENCES leagues(id)
        );""")
    conn.commit()
    conn.close()



if __name__ == '__main__':
    group()
