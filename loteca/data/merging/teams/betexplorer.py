import re
import sqlite3

import pandas as pd

from loteca.data.merging.teams.commons import FTeam, Tokens


STRIPCHARS = r" &'()-./’"

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


STATES = ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 
          'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 
          'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO']

def uncover_brazilian_string(betexp_string, df):
    """Given the string of a brazilian team and the DataFrame of brazilian team
    matches, returns a tuple (team_name, team_state, team_tokens).

    Args:
        betexp_string: the raw string for a team in the BetExplorer matches
        df: the DataFrame of brazilian team matches that are present in
            BetExplorer

    Returns:
        A tuple (team_name, team_state, team_tokens):
            team_name: the plain name of the team (without the tokens)
            team_state: a guess for the team state based on its name and the
                matches it played. None if not found.
            team tokens: an instance of Tokens, containing the values for UXX
                and Women.
    """
    str = betexp_string

    # extract tokens
    ## women
    str, women = re.subn(r'\bW\b', '', str)
    women = bool(women)

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
        str = re.sub(r'\(([a-zA-Z]{3})\)', str)

    ## save tokens
    tokens = Tokens(under, women)

    # the rest is the name of the team
    str = str.strip(STRIPCHARS)

    # get state by league
    leagues = set(df[(df.teamH == str) | (df.teamA == str)].league_name)
    for league in leagues:
        if league in LEAGUE_DICT:
            state = LEAGUE_DICT[league]
            break
    else:
        state = None

    # get state by name
    match = re.search(r'[ \-]([A-Z]{2})$', str)
    if match and match.group(1) in STATES:
        if state is None:
            state = match.group(1)

    # lowercase state
    state = state.lower() if state else None

    return (str, state, tokens)

def extract_world_name(betexplorer_string):
    """Extract the team name from a BetExplorer team string.

    Args:
        betexplorer_string: the raw betexplorer string, e.g. "AIK (Swe)".

    Returns:
        The plain name for the team (not formatted). E.g.: "AIK"
    """
    str = betexplorer_string

    # extract tokens
    ## women
    str, women = re.subn(r'\bW\b', '', str)
    women = bool(women)

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
        str = re.sub(r'\(([a-zA-Z]{3})\)', '', str)

    ## save tokens
    tokens = Tokens(under, women)

    # the rest is the name of the team
    str = str.strip(STRIPCHARS)

    return str

def format_name(name):
    return name.lower()

def create_world_fname_dict(IN_DB):
    """Create a dictionary that maps fnames into names. This will consider all
    the matches in the DB that didn't happen in Brazil.

    Args:
        IN_DB: the path to the database file that contains BetExplorer
            information

    Returns:
        A dictionary that maps BetExplorer fnames (formatted/standardized names)
        into BetExplorer original names, for all the teams that played
        non-brazilian games.
    """
    dict = {}

    conn = sqlite3.connect(IN_DB)
    df = pd.read_sql_query("SELECT teamH, teamA FROM matches WHERE league_category != 'brazil'", conn)
    conn.close()

    strings = sorted(set(df.teamH) | set(df.teamA))
    for string in strings:
        name = extract_world_name(string)
        fname = format_name(name)
        dict[fname] = name

    return dict

def create_brazilian_fteam_dict(IN_DB):
    """Creates a dictionary that maps fteams into names. This will consider all
    the matches that happened in Brazil.


    Args:
        IN_DB: location to the database where the BetExplorer matches are saved
    
    Returns:
        A dictionary that maps BetExplorer fteams (formatted name + state) into
        BetExplorer original names, for all the teams that played brazilian
        games.

        For some teams, the value of 'state' is unknown, so, we replace it with
        None.
    """
    dict = {}

    conn = sqlite3.connect(IN_DB)
    df = pd.read_sql_query("SELECT teamH, teamA, league_name FROM matches WHERE league_category == 'brazil'", conn)
    conn.close()
    
    strings = sorted(set(df.teamH) | set(df.teamA))
    for string in strings:
        name, state, tokens = uncover_brazilian_string(string, df)
        fname = format_name(name)
        fteam = FTeam(fname, state)
        dict[fteam] = name

    return dict

def generate_string(name, tokens):
    str = name
    under, women = tokens

    if under:
        str += ' U{}'.format(under)
    if women:
        str += ' W'

    return str
