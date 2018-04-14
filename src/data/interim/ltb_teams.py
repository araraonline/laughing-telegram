from collections import defaultdict
import logging

import click
from unidecode import unidecode

from src.data.interim.teams import betexplorer, loteca
from src.util import load_pickle, save_pickle


def standardize_country(name):
    """Standardize country name
    """
    from unidecode import unidecode
    return unidecode(name).lower()


def generate_countries_dict(in_countries_dict):
    """Generate the countries dict

    This dictionary will be able to translate loteca team fnames into
    betexplorer team fnames.

    For example:

        >>> countries_dict['brasil']
        'brazil'
    """
    # load countries
    countries = load_pickle(in_countries_dict)

    # standardize country names
    _sc = standardize_country
    countries = {_sc(k): _sc(v) for k, v in countries.items()}

    # manual updates
    updates = {
        'bosnia herzegovina': 'bosnia & herzegovina',
        'camaroes': 'cameroon',
        'costa do marfim': 'ivory coast',
        'escocia': 'scotland',
        'estados unidos': 'usa',
        'inglaterra': 'england',
        'irlanda do norte': 'northern ireland',
        'pais de gales': 'wales',
        'rep.tcheca': 'czech republic',
        'republica tcheca': 'czech republic',
        'servia e montenegro': 'serbia and montenegro',
        'taiti': 'tahiti',
    }
    countries.update(updates)

    return countries


def is_same_team(loteca_team, betexp_team, countries_dict):
    """Check if two teams are the same
    """
    lt = loteca_team
    be = betexp_team

    # strict restrictions
    if lt.women_flag != be.women_flag:
        return False
    if lt.under != be.under:
        return False
    if (lt.state and be.state and
          lt.state != be.state):
        return False

    # split case
    if not lt.state and not lt.country:
        # country team
        return countries_dict[lt.fname] == be.fname
    elif lt.country:
        # teams outside of brazil
        return (be.state is None and
                  be.fname == lt.fname)
    else:
        # teams from brazil
        return (lt.state == be.state and
                  lt.fname_without_state == be.fname_without_state)


def generate_ltb_teams_dict(loteca_teams, betexp_teams, countries_dict):
    """Generate the dict itself

    Read the CLI docstring for more information.
    """
    LOTECA_MAX_SIZE = max(len(t.fname) for t in loteca_teams)

    # generate dict
    ltb_dict = defaultdict(set)
    for loteca_team in loteca_teams:
        matching_teams = [t
                          for t in betexp_teams
                          if is_same_team(loteca_team, t, countries_dict)]
        betexp_fnames = set([t.fname for t in matching_teams])
        ltb_dict[loteca_team.fname] |= betexp_fnames

    # log founds
    logging.info("Found teams:")
    for loteca_fname, betexp_fnames in sorted(ltb_dict.items()):
        msg = "{loteca_fname!s:>{loteca_max_size}} -> {found}"
        msg = msg.format(loteca_fname=loteca_fname,
                         loteca_max_size=LOTECA_MAX_SIZE,
                         found=betexp_fnames if betexp_fnames else "{}")
        log_level = logging.WARNING if len(betexp_fnames) > 1 else logging.INFO
        logging.log(log_level, msg)

    return ltb_dict


@click.command()
@click.argument('in-betexp-db', type=click.Path(exists=True))
@click.argument('in-loteca-matches', type=click.Path(exists=True))
@click.argument('in-countries-dict', type=click.Path(exists=True))
@click.argument('out-ltb-teams', type=click.Path(writable=True))
def CLI(in_betexp_db, in_loteca_matches, in_countries_dict, out_ltb_teams):
    """Creates a dictionary that maps loteca teams into betexplorer teams

    \b
    Inputs:
        betexp-db (sqlite3): The database containing BetExplorer matches.
        loteca-matches (pkl): A DatFrame containing processed loteca matches.
        countries-dict (pkl): A dictionary that maps portuguese country names
            into english country names.

    \b
    Outputs:
        ltb-teams (pkl): A dictionary that will map (loteca team string ->
            set(BetExplorer team string)). The values of the dictionary are
            sets because we need to deal with cases where one loteca team maps
            to more than one BetExplorer teams.
    """
    click.echo("Preparing teams...")
    loteca_teams = loteca.retrieve_teams(in_loteca_matches)
    betexp_teams = betexplorer.retrieve_teams(in_betexp_db)

    click.echo("Generating countries dictionary...")
    countries_dict = generate_countries_dict(in_countries_dict)

    click.echo("Generating Loteca to BetExplorer teams dictionary...")
    ltb_teams = generate_ltb_teams_dict(
            loteca_teams, betexp_teams, countries_dict)

    click.echo("Saving...")
    save_pickle(out_ltb_teams, ltb_teams)


if __name__ == '__main__':
    CLI()
