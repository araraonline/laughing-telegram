import re
import sqlite3
import sys
from urllib.parse import urlparse

import click
import parsel

sys.path.append('../../../..')
from loteca.data.raw.util import requests_retry_session


def create_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leagues (
            category text NOT NULL,
            name text NOT NULL,
            year text NOT NULL,
            url text NOT NULL,
            scraped INTEGER,
            complete INTEGER,
            PRIMARY KEY(category, name, year)
            );""")

def save_league(cursor, category, name, year, url):
    url = process_url(url, year)
    if not url:
        return

    cursor.execute("""
        INSERT OR IGNORE
        INTO leagues (category, name, year, url, scraped, complete)
        VALUES (?,?,?,?,?,?);""", [category, name, year, url, False, None])

def process_url(league_url, year):
    url = league_url
    
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
@click.option('--start-year', type=click.INT)
def scrap_leagues(category, start_year):
    category = '-'.join(category.lower().split())
    start_year = (start_year or 0)
    
    url = 'http://www.betexplorer.com/soccer/{}/'.format(category)

    # connect to database
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()

    # create table
    create_table(cursor)

    # retrieve and save leagues
    session = requests_retry_session(total=10, backoff_factor=0.3)
    response = session.get(url)
    selector = parsel.Selector(response.text)

    for yearly_list in selector.css('tbody'):
        year = yearly_list.css('th::text').extract_first()    
        if int(year[-4:]) < start_year:
            continue

        for anchor in yearly_list.css('a'):
            name = anchor.css('::text').extract_first()
            url = anchor.css('::attr(href)').extract_first()
            save_league(cursor, category, name, year, url)
        
    # commit changes
    conn.commit()
    conn.close()


if __name__ == '__main__':
    scrap_leagues()
