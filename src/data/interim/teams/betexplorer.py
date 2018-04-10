import logging
import re
import sqlite3

import pandas as pd

from src.util import re_strip
from src.data.interim.teams.commons import Team


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


def parse_string(betexplorer_string):
    """Parse a BetExplorer team string

    Check out the return statement.
    """
    str = betexplorer_string

    # flags
    str, am = re.subn(r'\(Am\)', '', str)
    str, women = re.subn(r'\bW\b', '', str)
    am_flag = am > 0
    women_flag = women > 0

    # under XX
    under = re.search(r'\bU(\d{2})\b', str)
    if under:
        under = int(under.group(1))
        str = re.sub(r'\bU\d{2}\b', '', str)
    else:
        under = None

    # country
    country = re.search(r'\(([a-zA-Z]{3})\)', str)
    if country:
        country = country.group(1)
        str = re.sub(r'\(([a-zA-Z]{3})\)', '', str)
    else:
        country = None

    # the rest is the name of the team
    str = re_strip(str)

    return str, am_flag, women_flag, under, country


def format_name(name):
    return name.lower()


def generate_states_dict(conn):
    """Generates a dict that maps (BE fname -> BE state)

    If we could not guess the state, it won't be present in the dictionary.

    In case there are more than one possible states for a given fname, the
    function will log an error and set the state to UN.
    """
    # load data
    q = """
        SELECT team_h, team_a, league_name
        FROM betexp_matches
        WHERE league_category == 'brazil'
        """
    df = pd.read_sql_query(q, conn)

    # preprocess dataframe
    # here we are creating a dataframe with the
    # following columns: 'fname', 'string' 'league_state'
    df['league_state'] = df.league_name.apply(lambda x: LEAGUE_DICT.get(x))

    df = pd.concat([
        df[['team_h', 'league_state']].rename(columns={'team_h': 'string'}),
        df[['team_a', 'league_state']].rename(columns={'team_a': 'string'})
    ], axis=0)

    df['fname'] = df.string.apply(lambda x: format_name(parse_string(x)[0]))

    # generate dict
    # we want each fname to correspond to exactly one state
    dict = {}
    for fname, _df in df.groupby('fname'):
        states = set(_df.league_state) - {None}

        if len(states) == 0:
            continue
        elif len(states) == 1:
            dict[fname] = states.pop()
        else:
            msg = "Found multiple states for fname '{}'"
            msg = msg.format(fname)
            logging.error(msg)
            dict[fname] = 'UN'

    return dict


def retrieve_out_teams(conn):
    # retrieve team strings
    c = conn.cursor()

    c.execute("SELECT team_h FROM betexp_matches WHERE league_category != 'brazil'")
    teams_h = set([r[0] for r in c.fetchall()])

    c.execute("SELECT team_a FROM betexp_matches WHERE league_category != 'brazil'")
    teams_a = set([r[0] for r in c.fetchall()])

    c.close()
    conn.commit()

    strings = teams_h | teams_a

    # generate Team objects
    teams = []
    for string in strings:
        name, am_flag, women_flag, under, country = parse_string(string)
        fname = format_name(name)
        team = Team(string, name, fname,
                    am_flag=am_flag, women_flag=women_flag,
                    country=country, under=under)
        teams.append(team)

    return teams


def retrieve_brazilian_teams(conn):
    # retrieve team strings
    c = conn.cursor()
    c.execute("SELECT team_h FROM betexp_matches WHERE league_category == 'brazil'")
    teams_h = set([r[0] for r in c.fetchall()])
    c.execute("SELECT team_a FROM betexp_matches WHERE league_category == 'brazil'")
    teams_a = set([r[0] for r in c.fetchall()])
    c.close()
    conn.commit()

    strings = teams_h | teams_a

    # generate Team objects
    teams = []
    state_dict = generate_states_dict(conn)
    for string in strings:
        name, am_flag, women_flag, under, country = parse_string(string)
        fname = format_name(name)
        state = state_dict.get(fname)
        team = Team(string, name, fname, am_flag=am_flag,
                    women_flag=women_flag, country=country,
                    state=state, under=under)
        teams.append(team)

    return teams


def retrieve_teams(in_betexp_db):
    """Retrieve teams from BetExplorer

    Args:
        in_betexp_db: The SQLite file where the BetExplorer matches are saved.

    Returns:
        A list of Team objects (commons).
    """
    conn = sqlite3.connect(in_betexp_db)
    out_teams = retrieve_out_teams(conn)
    brazilian_teams = retrieve_brazilian_teams(conn)
    conn.close()

    return out_teams + brazilian_teams


def generate_string(team, use_country=False):
    """Generates a new BetExplorer team string

    Args:
        team: A Team object (commons). Its name must correspond to the desired
            BetExplorer name.
        use_country: Whether the country abbreviation must appear in the
            generated string.

    Returns:
        A BetExplorer string like it should be found in the database.

    Note:
        The "(Am)" token is ignored.
    """
    raise NotImplementedError  # check the use of this function

    str = team.name

    if team.under:
        str += ' U%s' % team.under
    if team.women_flag:
        str += ' W'
    if use_country and team.country:
        str += ' (%s)' % team.country.capitalize()

    return str
