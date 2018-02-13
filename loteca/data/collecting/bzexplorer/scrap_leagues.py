import urllib.parse
import re
import requests
import parsel
import click

from db import save_leagues_to_db


BASE_CATEGORY_URL =  r'http://www.betexplorer.com/soccer/'

def get_category_url(category):
    return 'http://www.betexplorer.com/soccer/{}/'.format(category)

def get_league_url(url, year):
    """Given a league url, it does 3 things:
    
    - First, it prepends the base of the url (betexplorer.com...) to the url so it can
      be requested
    - Second, it make urls with queries return None. These URLs should not be scraped because
      their original version are in another place. (for example, a World Cup link in the South
      America page)
    - Third, it adds an year to the leagues that don't have an year in it. This is important 
      because the URLs get changed as the yearr passes, but, the 'league-YEAR' model always
      work.
      
    The year argument is a string of the type: ('2014' or ''2013/2014')
    """
    # prepend URL
    if not url.startswith('http'):
        url = 'http://www.betexplorer.com' + url
    
    # ignore URLs with queries
    querystr = urllib.parse.urlparse(url).query
    if querystr:
        return None
    
    # remove last bar from URL
    if url.endswith('/'):
        url = url[:-1]
        
    # add year to yearless URLs
    beginning, end = url.rsplit('/', 1)
    if not re.match(r'.*\d{4}$', end):
        end = end + '-' + '-'.join(year.split('/'))   
    url = beginning + '/' + end
        
    # put the bar back
    url = url + '/'
    
    return url

def get_leagues(response, category):
    leagues = []

    selector = parsel.Selector(response.text)
    yearly_lists = selector.css('tbody')
    for yearly_list in yearly_lists:
        year = yearly_list.css('th::text').extract_first()    
        league_names = yearly_list.css('a::text').extract()
        league_urls = yearly_list.css('a::attr(href)').extract()
        
        for league_name, league_url in zip(league_names, league_urls):
            league_url = get_league_url(league_url, year)
            if league_url is None:
                continue

            leagues.append({
                'category': category,
                'name': league_name,
                'year': year,
                'url': league_url,
                'scraped': False,
                'complete': None,
            })

    return leagues

@click.command()
@click.argument('category')
@click.argument('db_loc', type=click.Path(exists=True))
def retrieve_leagues(category, db_loc):
    # category must be lwoercase, dash-separated
    category = '-'.join(category.lower().split())

    # get category url
    url = get_category_url(category)

    # scrap leagues
    response = requests.get(url)
    leagues = get_leagues(response, category)

    # save to database
    save_leagues_to_db(db_loc, leagues)


if __name__ == '__main__':
    retrieve_leagues()
