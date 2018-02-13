import click

from db import import retrieve_leagues_from_db, save_basicmatches_to_db, save_leagues_to_db


@click.command()
@click.argument('db_loc', type=click.Path(exists=True))
def scrap_matches(db_loc):
    leagues = retrieve_leagues_from_db(db_loc)
    for league in leagues:
        if not league['scraped'] or \
                    (league['scraped'] and not league['complete']):
            # check if league is complete
            complete = check_league_complete(league)

            # collect matches
            matches = get_league_matches(league)

            # save matches
            save_basicmatches_to_db(db_loc, matches)

            # update league
            league['scraped'] = True
            league['complete'] = complete
            save_leagues_to_db(db_loc, [league])
