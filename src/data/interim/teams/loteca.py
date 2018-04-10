import re

from unidecode import unidecode

from src.data.interim.teams.commons import Team
from src.util import load_pickle, re_strip


REPLACEMENTS = {
                'sao jose (pa' : 'sao jose',
                       'a b c' : 'abc',
           'atalanta bergamas' : 'atalanta',
                 'boa esporte' : 'boa esporte clube',
                'cfz brasilia' : 'cfz',
           'deporti la coruna' : 'deportivo la coruna',
               'e c democrata' : 'democrata',
    'fluminense feira santana' : 'fluminense',
                   'ji-parana' : 'ji parana',
               'p.  desportos' : 'portuguesa',
                 's. bernardo' : 'sao bernardo',
                    's. paulo' : 'sao paulo',
                     's.bento' : 'sao bento',
                'uniao s.joao' : 'uniao sao joao',
                       'vasco' : 'vasco da gama',
          'xv nov. piracicaba' : 'xv piracicaba',
}


def parse_string(loteca_string):
    """Parse a loteca string, extracting its token info

    See the return statement for the result.
    """
    str = loteca_string

    # simple tokens

    # re.subn will substitute the string and also return the
    # number of substitutions made (we are using it as a
    # flag)
    str, u20 = re.subn(r'\bSUB[ \-]?20\b', '', str, flags=re.I)
    str, junior = re.subn(r'\bJ[ÚU]NIOR\b', '', str, flags=re.I)
    str, women = re.subn(r'^F\b', '', str, flags=re.I)
    under = 20 if (u20 or junior) else None
    women_flag = women > 0

    str = re_strip(str)

    # complex tokens (state, country and name)
    if '/' in str:
        name, other = str.rsplit('/', 1)
        name = re_strip(name)
        other = re_strip(other)

        if len(other) == 2:
            country = None
            state = other.upper()
        elif len(other) == 3:
            country = other.upper()
            state = None
        else:
            raise ValueError("Bad loteca string: {}".format(str))
    else:
        name = str
        country = None
        state = None

    # return a tuple
    return name, under, women_flag, state, country


def format_name(loteca_name):
    """Format the loteca name to achieve a default format. For example, this
    would transform  the word "POÇOS DE CALDAS " into "pocos de caldas".
    """
    name = loteca_name
    name = unidecode(name)
    name = name.lower()
    name = re_strip(name)

    # we make some replacements just to standardize some
    # names that are present in multiple forms
    name = REPLACEMENTS.get(name, name)

    return name


def retrieve_teams(in_loteca_matches):
    """Load teams from loteca

    Args:
        - in_loteca_matches: Location of a .pkl file that contains the
              processed loteca matches.

    Returns:
        A list of Team objects (`commons`).
    """
    matches = load_pickle(in_loteca_matches)
    strings = set(matches.team_h) | set(matches.team_a)

    teams = []
    for string in strings:
        name, under, women_flag, state, country = parse_string(string)
        fname = format_name(name)
        team = Team(string, name, fname, women_flag=women_flag,
                    country=country, state=state, under=under)
        teams.append(team)

    return teams
