from collections import namedtuple
import sqlite3

import click
from parsel import Selector

from src.data.raw.util import requests_retry_session


League = namedtuple('League', 'category, name, year, url')
Match = namedtuple('Match', 'id, url, team_h, team_a, date, score, scoremod')


def create_table(conn):
    """Create the matches table
    """
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS betexp_matches (
            id               TEXT  NOT NULL,
            url              TEXT  NOT NULL,
            league_category  TEXT  NOT NULL,
            league_name      TEXT  NOT NULL,
            league_year      TEXT  NOT NULL,
            team_h           TEXT  NOT NULL,
            team_a           TEXT  NOT NULL,
            date             TEXT  NOT NULL,
            score            TEXT  NOT NULL,
            scoremod         TEXT  NOT NULL,
                PRIMARY KEY (id),
                FOREIGN KEY (league_category, league_name, league_year)
                REFERENCES betexp_leagues (category, name, year)
        )
        """)
    cursor.close()
    conn.commit()


def get_leagues(conn):
    """Retrieve the leagues that must be scraped
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT category, name, year, url
        FROM betexp_leagues
        WHERE (scraped == 0) OR (scraped == 1 AND finished == 0)
        ORDER BY year ASC
    """)
    leagues = cursor.fetchall()
    cursor.close()
    conn.commit()

    return [League(*l) for l in leagues]


def check_finished(league):
    """Check if a league is finished (no more matches to be played)
    """
    session = requests_retry_session(total=10, backoff_factor=0.3)
    response = session.get(league.url)
    return 'No upcoming matches to be played.' in response.text


def retrieve_other_urls(response):
    """Retrieve URLs for other stages of a league

    What is returned are actually query strings that must be added to the end
    of each 'results' URL.
    """
    selector = Selector(response.text)
    q = ('.list-tabs--secondary a.list-tabs__item__in:not(.current)'
           '::attr(href)')

    urls = selector.css(q).extract()
    urls = set(urls) - {'javascript:void(0);'}
    urls = sorted(urls)

    return urls


def retrieve_page_matches(response):
    """Scrap matches for a page of a certain league
    """
    matches = []

    selector = Selector(response.text)
    _rows = selector.css('.table-main tr')
    for _row in _rows:
        if _row.css('th'):
            # it is a header
            continue

        url = _row.css('td:nth-of-type(1) a::attr(href)').extract_first()
        if not url.startswith('http'):
            url = 'http://www.betexplorer.com' + url
        teams = _row.css('td:nth-of-type(1) span ::text').extract()
        score = _row.css('td:nth-of-type(2) a::text').extract_first() or ''
        scoremod = _row.css('td:nth-of-type(2) a span::text').extract_first() or ''
        date = _row.css('td:nth-of-type(6)::text').extract_first()
        id = url.split('/')[-2]

        match = Match(id, url, teams[0], teams[1], date, score, scoremod)
        matches.append(match)

    return matches


def retrieve_matches(league):
    """Retrieve matches for a certain league

    This function may crawl over several links.
    """
    session = requests_retry_session(total=10, backoff_factor=0.3)

    url = league.url + 'results/'
    response = session.get(url)

    matches = []
    matches += retrieve_page_matches(response)
    for url in retrieve_other_urls(response):
        url = league.url + 'results/' + url
        response = session.get(url)
        matches += retrieve_page_matches(response)

    return matches


def save_match(cursor, league, match):
    """Save match to database
    """
    m = match
    l = league

    cursor.execute("""
        INSERT OR IGNORE INTO betexp_matches
        VALUES (?,?,?,?,?,?,?,?,?,?)
        """, [m.id, m.url,
              l.category, l.name, l.year,
              m.team_h, m.team_a, m.date, m.score, m.scoremod])


def retrieve_and_save_matches(conn):
    """Retrieve leagues matches and save them
    """
    leagues = get_leagues(conn)
    for league in leagues:
        click.echo("Retrieving matches from {}".format(league.url))
        is_league_finished = check_finished(league)
        matches = retrieve_matches(league)

        # save
        l = league
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE betexp_leagues
            SET
              scraped = 1,
              finished = ?
            WHERE
              category = ?
              AND name = ?
              AND year = ?
            """, [is_league_finished, l.category, l.name, l.year])

        for match in matches:
            save_match(cursor, league, match)

        cursor.close()
        conn.commit()


@click.command()
@click.argument('io-db', type=click.Path())
def CLI(io_db):
    """Collect matches from BetExplorer leagues

    This will run over all leagues, checking if they were scraped or not, and,
    if they are matches yet to come or not. If the league has not been scraped
    yet or if there are still matches to be played, it will be scraped.

    \b
    Inputs:
        db (sqlite3): The database where the BetExplorer leagues are saved. This
            will also be used as a checklist of what has been scraped or not.

    \b
    Outputs:
        db (sqlite3): The database where the BetExplorer matches will be saved.
            These matches only carry general information visible from the
            league page.
    """
    conn = sqlite3.connect(io_db)

    create_table(conn)
    retrieve_and_save_matches(conn)

    conn.close()


if __name__ == '__main__':
    CLI()
