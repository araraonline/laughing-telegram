import re
import sqlite3
from collections import namedtuple
from urllib.parse import urlparse

import click
from parsel import Selector

from src.data.raw.util import requests_retry_session


League = namedtuple('League', 'category, name, year, url')


def create_table(conn):
    """Create the leagues table
    """
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS betexp_leagues (
          category  TEXT     NOT NULL,
          name      TEXT     NOT NULL,
          year      TEXT     NOT NULL,
          url       TEXT     NOT NULL,
          scraped   INTEGER  NOT NULL DEFAULT 0,
          finished  INTEGER  ,

          PRIMARY KEY(category, name, year)
        )""")
    cursor.close()
    conn.commit()


def scrap_leagues(category):
    """Scrap leagues from a given category
    """
    session = requests_retry_session(total=10, backoff_factor=0.3)

    url = 'http://www.betexplorer.com/soccer/{}/'.format(category)
    click.echo('Retrieving leagues from {}'.format(url))

    response = session.get(url)
    selector = Selector(response.text)

    leagues = []
    _table = selector.css('tbody')
    for _yearly_list in _table:
        year = _yearly_list.css('th::text').extract_first()
        for _anchor in _yearly_list.css('a'):
            name = _anchor.css('::text').extract_first()
            url = _anchor.css('::attr(href)').extract_first()
            url = prepare_league_url(url, year)
            if url:
                leagues.append(League(category, name, year, url))

    return leagues


def save_leagues(conn, leagues):
    """Save leagues to the database

    This will execute a transaction.
    """
    cursor = conn.cursor()
    for league in leagues:
        l = league
        cursor.execute("""
            INSERT OR IGNORE INTO betexp_leagues (
              category,
              name,
              year,
              url
            )
            VALUES (?, ?, ?, ?)
            """, [l.category, l.name, l.year, l.url])
    cursor.close()
    conn.commit()


def prepare_league_url(url, year):
    """Prepares a league URL for saving

    Steps:
    - Convert relative URL into absolute URL

    - Add year to the end of the URL

      For example, http://www.betexplorer.com/soccer/brazil/serie-a/ can become
      http://www.betexplorer.com/soccer/brazil/serie-a-2018/.

      The second URL does not vary with the time.

    - Any URLs with queries halt the process and return None.

      This behaviour happens because we want to avoid URLs with queries (they
      are duplicates).
    """
    # prepend URL
    if not url.startswith('http'):
        url = 'http://www.betexplorer.com' + url

    # ignore URLs with queries
    querystr = urlparse(url).query
    if querystr:
        return None

    # add year to yearless URLs
    beginning, end, _ = url.rsplit('/', 2)
    if not re.match(r'.*\d{4}$', end):
        end = end + '-' + '-'.join(year.split('/'))

    return "{}/{}/".format(beginning, end)


@click.command()
@click.argument('category')
@click.argument('start-year', type=click.INT)
@click.argument('out-db', type=click.Path())
def CLI(category, start_year, out_db):
    """Extracts leagues from the league pages (see example at [1])

    \b
    Arguments:
        category (str): The category to extract leagues from. Must be all
            lowercase and dash splitted (for example, 'south-america').
        start-year (int): Only leagues that happened at or after said year will
            be recorded.

    \b
    Outputs:
        db (sqlite3): A database object to save the leagues to.

    \b
    [1]: http://www.betexplorer.com/soccer/brazil/
    """
    conn = sqlite3.connect(out_db)

    create_table(conn)
    leagues = scrap_leagues(category)
    leagues = [l for l in leagues if start_year <= int(l.year[-4:])]
    save_leagues(conn, leagues)

    conn.close()


if __name__ == '__main__':
    CLI()
