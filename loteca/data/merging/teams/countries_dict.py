import json
import pickle

import click
from unidecode import unidecode


def get_country_translations(loc1, loc2):
    """Return a dictionary of country translations, based on the format of:
    https://github.com/umpirsky/country-list

    Note: please use the json files (as in):
    https://github.com/umpirsky/country-list/blob/master/data/pt_BR/country.json

    Args:
        loc1: *local* path to the dictionary that will provide our
            translation keys.
        loc2: *local* path to the dictionary that will provide our
            translation values.

    Returns:
        A dict (name of the country -> name of the country), based on the lists
        found at loc1 and loc2.
    """
    ret = {}

    with open(loc1, mode='rb') as fp:
        d1 = json.load(fp)
    with open(loc2, mode='rb') as fp:
        d2 = json.load(fp)

    for abbr, name in d1.items():
        ret[name] = d2[abbr]

    return ret

def standardize(country):
    return unidecode(country).lower()


@click.command()
@click.argument('in-en-dictionary', type=click.Path(exists=True))
@click.argument('in-pt-dictionary', type=click.Path(exists=True))
@click.argument('out-countries-dict', type=click.Path(writable=True))
def generate_countries_dict(in_en_dictionary, in_pt_dictionary, out_countries_dict):
    """Generates a dictionary that will map brazilian country names into english
    country names. This is made to be used in converting Loteca team names into
    BetExplorer team names, so, it is pretty specific.

    The inputs are json files downloaded from this repository:
    https://github.com/umpirsky/country-list

    \b
    The resulting dictionary will be of the form: 
        LOTECA_FNAME -> BETEXPLORER_FNAME

    \b
    LOTECA_FNAME and BETEXPLORER_FNAME refers to the formatted (standardized)
    name of the countries as present in loteca and betexplorer matches,
    respectively.

    \b
    Args:
        in_en_dictionary: the location of the english .json input dictionary
        in_pt_dictionary: the location of the pt_BR .json input dictionary
        out_countries_dict: the output location where our dict will be saved

    The output format is .pkl
    """
    # generate dictionary
    translations = get_country_translations(in_pt_dictionary, in_en_dictionary)

    # standardize format
    translations = {standardize(k): standardize(v) for k, v in translations.items()}

    # make some changes so it works for the loteca -> betexplorer conversion
    d = translations
    d['bosnia herzegovina'] = 'bosnia & herzegovina'
    d['camaroes'] = 'cameroon'
    d['costa do marfim'] = 'ivory coast'
    d['escocia'] = 'scotland'
    d['estados unidos'] = 'usa'
    d['inglaterra'] = 'england'
    d['irlanda do norte'] = 'northern ireland'
    d['pais de gales'] = 'wales'
    d['rep.tcheca'] = 'czech republic'
    d['republica tcheca'] = 'czech republic'
    d['servia e montenegro'] = 'serbia and montenegro'
    d['taiti'] = 'tahiti'

    # save
    with open(out_countries_dict, mode='wb') as fp:
        pickle.dump(d, fp)

    return 0


if __name__ == '__main__':
    generate_countries_dict()
