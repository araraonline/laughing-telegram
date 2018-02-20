import re
from unidecode import unidecode

from loteca.data.merging.teams.commons import Tokens


STRIPCHARS = ' ()-./'

def split_string(loteca_string):
    str = loteca_string

    # tokens
    str, u20 = re.subn(r'\bSUB[ \-]?20\b', '', str, flags=re.I)
    str, junior = re.subn(r'\bJ[ÚU]NIOR\b', '', str, flags=re.I)
    str, women = re.subn(r'^F\b', '', str, flags=re.I)
    tokens = Tokens(20 if u20 or junior else 0, bool(women))
    str = str.strip(STRIPCHARS)
    
    # name and state
    if '/' in str:
        name, state = str.rsplit('/', 1)
    else:        
        name, state = (str, 'w')

    # clean
    name = name.strip(STRIPCHARS)
    state = state.strip(STRIPCHARS).lower()

    return name, state, tokens


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

def format_name(loteca_name):
    """Format the loteca name to achieve a default format. For example, this
    would transform  the word "POÇOS DE CALDAS " into "pocos de caldas".
    """
    name = loteca_name
    name = unidecode(name)  # replace strange characters (ç -> c)
    name = name.lower()  # lowercase
    name = name.strip(STRIPCHARS)  # clean ends

    name = REPLACEMENTS.get(name, name)  # 
    return name
