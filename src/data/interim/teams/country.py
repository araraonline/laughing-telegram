import json

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


def make_translations(in_countries_en, in_countries_ptbr):
    """Generate dictionary to translate Loteca to BetExplorer country names

    Args:
        in_countries_en: the location of the english dictionary (json)
        en_countries_ptbr: the location of the ptbr dictionary (json)'

    Note:
        Both dictionaries should be downloaded from the following repository:
        https://github.com/umpirsky/country-list

    Returns:
        A dict (Loteca country fname -> BetExplorer country fname) for
        converting between names of country teams. All the keys and values are
        standardized, so make sure to use the formatted name instead of the raw
        name.
    """
    # generate dictionary
    translations = get_country_translations(in_countries_ptbr, in_countries_en)

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

    return d
