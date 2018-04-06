import sqlite3
from collections import namedtuple

import click
from parsel import Selector

from src.data.raw.util import requests_retry_session
from src.util import load_pickle


Odd = namedtuple('Odd', 'match_id, date, bookmaker, odd_type, odd_target, value')


def create_tables(conn):
    """Create tables for the odds extraction
    """
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS betexp_match_checklist (
          id       TEXT     NOT NULL,
          url      TEXT     NOT NULL,
          scraped  INTEGER  NOT NULL DEFAULT 0,

          PRIMARY KEY (id),
          FOREIGN KEY (id) REFERENCES matches (id)
        )""")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS betexp_odds (
          id          INTEGER  NOT NULL,
          match_id    TEXT     NOT NULL,
          date        TEXT     NOT NULL,
          bookmaker   TEXT     NOT NULL,
          odd_type    TEXT     NOT NULL,
          odd_target  TEXT     NOT NULL,
          value       NUMERIC  NOT NULL,

          PRIMARY KEY (id),
          FOREIGN KEY (match_id) REFERENCES matches (id)
        )""")

    conn.commit()


def insert_matches(conn, matches_ids):
    """Insert unscraped matches into the scraping checklist
    """
    cursor = conn.cursor()
    for match_id in matches_ids:
        cursor.execute("SELECT url FROM betexp_matches WHERE id == ?", [match_id])
        url = cursor.fetchone()[0]

        cursor.execute("""
            INSERT OR IGNORE
            INTO betexp_match_checklist (id, url)
            VALUES (?, ?)
            """, [match_id, url])
    conn.commit()


def scrap_odds(match_id, match_url):
    """Scrap match odds from BetExplorer

    Odds not present in the page will be set a value of 0.0
    """
    # make the request and extract the response
    url = 'http://www.betexplorer.com/gres/ajax/matchodds.php?p=1&e={}&b=1x2'.format(match_id)
    headers = {
        'User-Agent': 'Dummy agent',
        'Referer': match_url
    }
    session = requests_retry_session(total=10, backoff_factor=0.3, status_forcelist=[104])
    response = session.get(url, headers=headers, timeout=5)
    body = response.json()['odds']

    # colelct the odds
    odds = []
    s = Selector(body)
    _rows = s.xpath('//tr[@data-originid]')
    for _row in _rows:
        bookmaker = _row.css('a::text').extract_first()

        _odds = _row.css('td.table-main__odds')
        archive_odds = _odds.css('::attr(data-odd)').extract()
        archive_dates = _odds.css('::attr(data-created)').extract()
        opening_odds = _odds.css('::attr(data-opening-odd)').extract()
        opening_dates = _odds.css('::attr(data-opening-date)').extract()

        # some bookmakers only have 2 odds, we skip them
        # for example (Unibet)
        # http://www.betexplorer.com/soccer/brazil/serie-a-2009/atletico-pr-atletico-mg/ABPNekAl/
        if len(archive_odds) < 3 or len(opening_odds) < 3:
            continue
        assert len(archive_odds) == 3
        assert len(opening_odds) == 3

        # impute missing values
        archive_odds = [odd or 0.0 for odd in archive_odds]
        opening_odds = [odd or 0.0 for odd in opening_odds]

        # archive odds
        odds.append(Odd(match_id, archive_dates[0], bookmaker, 'archive', '1', float(archive_odds[0])))
        odds.append(Odd(match_id, archive_dates[1], bookmaker, 'archive', 'X', float(archive_odds[1])))
        odds.append(Odd(match_id, archive_dates[2], bookmaker, 'archive', '2', float(archive_odds[2])))

        # opening odds
        odds.append(Odd(match_id, opening_dates[0], bookmaker, 'opening', '1', float(opening_odds[0])))
        odds.append(Odd(match_id, opening_dates[1], bookmaker, 'opening', 'X', float(opening_odds[1])))
        odds.append(Odd(match_id, opening_dates[2], bookmaker, 'opening', '2', float(opening_odds[2])))

    return odds


def save_odds(conn, match_id, match_odds):
    """Save the match odds to the database
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE betexp_match_checklist
        SET scraped = 1
        WHERE id == ?
        """, [match_id]
    )

    for odd in match_odds:
        q = """
            INSERT INTO betexp_odds (
              match_id,
              date,
              bookmaker,
              odd_type,
              odd_target,
              value
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """
        cursor.execute(q, [odd.match_id, odd.date, odd.bookmaker,
                           odd.odd_type, odd.odd_target, odd.value])

    cursor.close()
    conn.commit()


def scrap_and_save_odds(conn):
    """Scrap odds for matches on the checklist that have not been scraped yet

    The odds are then saved to the DB.
    """
    # retrieve matches that need to be scraped
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, url
        FROM betexp_match_checklist
        WHERE scraped == 0
        """)
    to_scrap = cursor.fetchall()
    cursor.close()
    conn.commit()

    # scrap and save odds
    for match_id, match_url in to_scrap:
        click.echo("Collecting odds from {}".format(match_url))
        odds = scrap_odds(match_id, match_url)
        save_odds(conn, match_id, odds)
        import time; time.sleep(1)


@click.command()
@click.argument('in-betexp-matches', type=click.Path(exists=True))
@click.argument('io-betexp-db', type=click.Path(exists=True))
def CLI(io_betexp_db, in_betexp_matches):
    """Collect odds from specified matches (BetExplorer)

    \b
    Inputs:
        betexp-matches (pkl): A list of ids corresponding to the BetExplorer
            matches whose odds must be retrieved.
        betexp-db (sqlite3): The database from which the BetExplorer URLs will
            be retrieved.

    \b
    Outputs:
        betexp-db (sqlite3): The database to which the BetExplorer odds for the
            matches will be saved.
    """
    matches_ids = load_pickle(in_betexp_matches)
    conn = sqlite3.connect(io_betexp_db)

    create_tables(conn)
    insert_matches(conn, matches_ids)
    scrap_and_save_odds(conn)

    conn.close()


if __name__ == '__main__':
    CLI()
