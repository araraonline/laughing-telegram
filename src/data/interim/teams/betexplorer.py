import logging
import re
import sqlite3
from collections import defaultdict

import click_log
import pandas as pd

from src.data.interim.teams.commons import Team, Tokens
from src.data.interim.teams.util import re_strip


logger = logging.getLogger('betexp-teams')
click_log.basic_config(logger)


LEAGUE_DICT = {
    'Campeonato Alagoano': 'AL',
    'Campeonato Baiano': 'BA',
    'Campeonato Brasiliense': 'DF',
    'Campeonato Carioca': 'RJ',
    'Campeonato Catarinense': 'SC',
    'Campeonato Cearense': 'CE',
    'Campeonato Gaucho': 'RS',
    'Campeonato Goiano': 'GO',
    'Campeonato Matogrossense': 'MT',
    'Campeonato Mineiro': 'MG',
    'Campeonato Paraense': 'PA',
    'Campeonato Paranaense': 'PR',
    'Campeonato Paulista': 'SP',    
    'Campeonato Pernambucano': 'PE',
    'Campeonato Potiguar': 'RN',
    'Campeonato Sergipano': 'SE',
    'Campeonato Sul-Matogrossense': 'MS',
    'Campeonato Paraibano': 'PB',
    'Campeonato Maranhense': 'MA',
    'Campeonato Piauiense': 'PI',
}

def generate_name_to_strings(df):
    """Generates a BetExplorer team name to BetExplorer team strings mapping

    Args:
        df: the dataframe from which the team names will be retrieved

    Returns:
        A dictionary that maps (BetExplorer name -> list of BetExplorer strings
        that generate that name).
    """
    dict = defaultdict(list)

    strings = set(df.teamH) | set(df.teamA)
    for string in strings:
        name, tokens = extract_tokens(string)
        dict[name].append(string)

    return dict

def guess_state(betexplorer_name, brazilian_df, name_to_strings):
    """Guess the state for a brazilian team

    This function will look through all the brazilian matches and, if the team
    played in a match that only happens in a certain state, we will assign this
    state to the team.

    Args:
        betexplorer_name: the raw BetExplorer team name (without tokens)
        brazilian_df: a DataFrame containing all the brazilian matches with the
            following columns: 'teamH', 'teamA' and 'league_name'
        name_to_strings: a dict (BetExplorer name -> list of BetExplorer strings
            that generate that name) for the brazilian teams

    Returns:
        A two lettered string representing the state of the team. The string is
        in lowercase. If no state was found, returns None.
    """
    df = brazilian_df

    leagues = set()
    strings = name_to_strings[betexplorer_name]
    for string in strings:
        sleagues = set(df[(df.teamH == string) | (df.teamA == string)].league_name)
        leagues |= sleagues

    states = set([LEAGUE_DICT[league] for league in leagues if league in LEAGUE_DICT])

    if len(states) == 0:
        return None
    elif len(states) == 1:
        return states.pop().lower()
    else:
        logger.warning('"%s" found in these states: %s' % (betexplorer_name, sorted(states)))
        return None

def extract_tokens(betexplorer_string):
    """Extract the tokens from a BetExplorer team string

    Args:
        betexplorer_string: raw betexplorer team string

    Returns:
        A tuple (betexplorer_name, tokens) where betexplorer_name is the name of
        the BetExplorer team without formatting and tokens is an object of type
        Tokens that contains meta information for the team.

        The Tokens itself contain the following variables:
            state: the state of the team (always None for this function)
            country: 3 letter country or None
            am: True or False (whether the string contains (Am)
            under: the integer value for UXX or 0
            women: True or False
    """
    str = betexplorer_string

    # tokens
    ## women
    str, women = re.subn(r'\bW\b', '', str)
    women = bool(women)

    # am
    str, am = re.subn(r'\(Am\)', '', str)
    am = bool(am)

    ## under XX
    under = re.search(r'\bU(\d{2})\b', str)
    if under:
        under = int(under.group(1))
        str = re.sub(r'\bU\d{2}\b', '', str)
    else:
        under = 0

    ## country
    country = re.search(r'\(([a-zA-Z]{3})\)', str)
    if country:
        country = country.group(1)
        country = country.lower()
        str = re.sub(r'\(([a-zA-Z]{3})\)', '', str)
    else:
        country = None

    # state
    state = None

    ## create tokens object
    tokens = Tokens(state, country, am, under, women)

    # the rest is the name of the team
    str = re_strip(str)

    return str, tokens

def format_name(name):
    return name.lower()

def generate_string(name, tokens, use_country=False):
    """Generates a new BetExplorer team string

    Args:
        name: the raw BetExplorer name (without tokens)
        tokens: a Tokens object
        use_country: a bool indicating whether we should append the country
            token to the string

    Returns:
        A BetExplorer string just like it should be found in the database.

    Note:
        The "(Am)" token is ignored, as we are not using it.
    """
    str = name
    if tokens.under:
        str += ' U%s' % tokens.under
    if tokens.women:
        str += ' W'
    if use_country and tokens.country:
        str += ' (%s)' % tokens.country.capitalize()

    return str

def retrieve_teams(in_betexp_db):
    """Retrieves a list of BetExplorer teams

    This will iterate over the BetExplorer database to retrieve the teams and
    them will process them. Brazilian teams will also contain information about
    the state they are from.

    Args:
        in_betexp_db: the location of the database to retrieve matches (and
            consequently teams) from

    Returns:
        A list of 'Team's, corresponding to the teams that played on the
        BetExplorer matches. Each Team is an object with the following
        attributes (from most processed to least processed):

        fname: standardized name of the team (used when comparing from
            different sources)
        name: raw name of the team (without tokens)
        string: raw name of the team (with tokens)
        tokens: a Tokens object
    """
    teams = []

    conn = sqlite3.connect(in_betexp_db)

    # international teams
    df = pd.read_sql_query("SELECT teamH, teamA FROM matches WHERE league_category != 'brazil'", conn)
    strings = set(df.teamH) | set(df.teamA)
    strings = sorted(strings)

    for string in strings:
        name, tokens = extract_tokens(string)
        fname = format_name(name)
        team = Team(fname, name, string, tokens)
        teams.append(team)

    # brazilian teams
    df = pd.read_sql_query("SELECT teamH, teamA, league_name FROM matches WHERE league_category == 'brazil'", conn)
    name_to_strings = generate_name_to_strings(df)
    strings = set(df.teamH) | set(df.teamA)
    strings = sorted(strings)

    for string in strings:
        name, tokens = extract_tokens(string)
        fname = format_name(name)

        # guess state
        state = guess_state(name, df, name_to_strings)
        tokens = tokens._replace(state=state)

        # save
        team = Team(fname, name, string, tokens)
        teams.append(team)

    conn.close()

    return teams
