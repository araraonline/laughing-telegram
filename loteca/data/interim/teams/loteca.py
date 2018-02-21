import re

import pandas as pd
from unidecode import unidecode

from loteca.data.interim.teams.commons import Team, Tokens
from loteca.data.interim.teams.util import re_strip


REPLACEMENTS = {
    'sao jose (pa': 'sao jose',                  # SÃO JOSÉ (PA)/RS
    'a b c': 'abc',                              # A B C/RN
    'atalanta bergamas': 'atalanta',             # ATALANTA BERGAMAS/ITA
    'boa esporte': 'boa esporte clube',          # BOA ESPORTE/MG
    'cfz brasilia': 'cfz',                       # CFZ BRASÍLIA/DF JUNIOR
    'deporti la coruna': 'deportivo la coruna',  # DEPORTI LA CORUNA/ESP
    'e c democrata': 'democrata',                # E C DEMOCRATA/MG
    'fluminense feira santana': 'fluminense',    # FLUMINENSE FEIRA SANTANA/BA
    'ji-parana': 'ji parana',                    # JI PARANÁ/RO JÚNIOR
    'p.  desportos': 'portuguesa',               # P. DESPORTOS/SP
    's. bernardo': 'sao bernardo',               # S. BERNARDO/SP
    's. paulo': 'sao paulo',                     # S. PAULO/SP
    's.bento': 'sao bento',                      # S.BENTO/SP
    'uniao s.joao': 'uniao sao joao',            # UNIÃO S.JOÃO/SP
    'vasco': 'vasco da gama',                    # VASCO/RJ
    'xv nov. piracicaba': 'xv piracicaba',       # XV NOV. PIRACICABA/SP
}

def extract_tokens(loteca_string):
    """Extracts the tokens from a loteca string

    Args:
        loteca_string: the raw loteca string whose tokens will be extracted

    Returns:
        A tuple (loteca_name, tokens) that contains the raw team name (without
        the tokens) and an object of type Tokens.

        The Tokens itself contain the following variables:
            state: 2 letter state or None
            country: 3 letter country or None
            am: always False for loteca
            under: 20 if 'sub20' or 0
            women: True or False
    """
    str = loteca_string

    # tokens
    str, u20 = re.subn(r'\bSUB[ \-]?20\b', '', str, flags=re.I)
    str, junior = re.subn(r'\bJ[ÚU]NIOR\b', '', str, flags=re.I)
    str, women = re.subn(r'^F\b', '', str, flags=re.I)
    str = re_strip(str)
    
    # name, country and state
    if '/' in str:
        name, other = str.rsplit('/', 1)
        name = re_strip(name)
        other = re_strip(other)
        if len(other) == 2:
            country = None
            state = other.lower()
        elif len(other) == 3:
            country = other.lower()
            state = None
        else:
            raise ValueError("Could not extract tokens for %s" % str)
    else:        
        name = str
        country = None
        state = None
    
    # normalize types
    am = False
    under = 20 if u20 or junior else 0
    women = bool(women)

    # create tokens object
    tokens = Tokens(state, country, am, under, women)

    return name, tokens

def format_name(loteca_name):
    """Format the loteca name to achieve a default format. For example, this
    would transform  the word "POÇOS DE CALDAS " into "pocos de caldas".
    """
    name = loteca_name
    name = unidecode(name)
    name = name.lower()
    name = re_strip(name)
    name = REPLACEMENTS.get(name, name)

    return name

def retrieve_teams(in_loteca_matches, start_round=366):
    """Retrieve a list o loteca teams

    This will only open the loteca matches file and extract/process the teams
    from it.
    
    Args:
        in_loteca_matches: a pkl file that contains loteca matches in a
            DataFrame
        start_round: first round to retrieve matches from
    
    Returns:
        A list of 'Team' objects. Each team object contains the following info:

        fname: standardized name of the team (used when comparing from
            different sources)
        name: raw name of the team (without tokens)
        string: raw name of the team (with tokens)
        tokens: a Tokens object
    """
    matches = pd.read_pickle(in_loteca_matches)
    matches = matches[matches.roundno >= start_round]

    strings = set(matches.teamH) | set(matches.teamA)
    strings = sorted(strings)

    teams = []
    for string in strings:
        name, tokens = extract_tokens(string)
        fname = format_name(name)
        team = Team(fname, name, string, tokens)
        teams.append(team)

    return teams
