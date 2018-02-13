import sqlite3
import click
import requests
import parsel


def create_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id text,
            url text,

            league_category text NOT NULL,
            league_name text NOT NULL,
            league_year text NOT NULL,

            teamH text NOT NULL,
            teamA text NOT NULL,
            date text NOT NULL,

            score text NOT NULL,
            scoremod text NOT NULL,

            PRIMARY KEY(id, league_category, league_name, league_year),
            FOREIGN KEY(league_category, league_name, league_year) REFERENCES leagues(category, name, year)
        );""")

def save_matches(cursor, response, category, name, year):
    selector = parsel.Selector(response.text)

    rows = selector.css('.table-main tr')
    for row in rows:
        if row.css('th'): continue  # it is a header

        url = row.css('td:nth-of-type(1) a::attr(href)').extract_first()
        teams = row.css('td:nth-of-type(1) span ::text').extract()    
        score = row.css('td:nth-of-type(2) a::text').extract_first() or ''
        scoremod = row.css('td:nth-of-type(2) a span::text').extract_first() or ''
        date = row.css('td:nth-of-type(6)::text').extract_first()

        id = url.split('/')[-2]

        cursor.execute("""
            INSERT OR IGNORE
            INTO matches (id, url, league_category, league_name, league_year, teamH, teamA, date, score, scoremod)
            VALUES (?,?,?,?,?,?,?,?,?,?)""", [id, url, category, name, year, teams[0], teams[1], date, score, scoremod])

def retrieve_other_urls(response, base_url):
    """Some leagues are composed of more than one pages.
    If this is the case, this function will return the urls
    to all the pages in tghe league that are not the current.
    
    You can scrape all those links later!
    """
    selector = parsel.Selector(text=response.text)      
    urls = selector.css('.list-tabs--secondary a.list-tabs__item__in:not(.current)::attr(href)').extract()
    urls = set(urls)
    urls = urls - set(['javascript:void(0);'])
    urls = sorted(urls)
    urls = [base_url + url for url in urls]
    
    return urls


# Direct interface with main function

def check_complete(url):
    response = requests.get(url)
    return 'No upcoming matches to be played.' in response.text

def save_all_matches(category, name, year, base_url, cursor):
    url = base_url + 'results/'
    response = requests.get(url)
    save_matches(cursor, response, category, name, year)

    for url in retrieve_other_urls(response, url):
        response = requests.get(url)
        save_matches(cursor, response, category, name, year)
    

# CLI

@click.command()
def collect_matches():
    # connect to database
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    
    # create table
    create_table(cursor)

    # iterate over leagues and save matches
    cursor.execute("""
        SELECT category, name, year, url
        FROM leagues
        WHERE (scraped == 0) OR (scraped == 1 AND complete == 0)
        ORDER BY year ASC
    ;""")
    leagues = cursor.fetchall()

    # iterate over leagues and save matches
    for category, name, year, url in leagues:
        click.echo("Collecting matches from {}".format(url))
        complete = check_complete(url)
        save_all_matches(category, name, year, url, cursor)
        cursor.execute("""
            UPDATE leagues
            SET scraped = 1, complete = ?
            WHERE category = ? AND name = ? AND year = ?
        ;""", [complete, category, name, year])
        conn.commit()

    # close db
    conn.close()


if __name__ == '__main__':
    collect_matches()
