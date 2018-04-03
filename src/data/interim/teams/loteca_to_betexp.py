import logging
import pickle
import re
from collections import defaultdict

import click
import click_log

import src.data.interim.teams.betexplorer as betexplorer
import src.data.interim.teams.country as country
import src.data.interim.teams.loteca as loteca
from src.data.interim.teams.util import re_strip


logger = logging.getLogger('loteca-betexp-teams-dict')
click_log.basic_config(logger)


def remove_state_from_name(name, state):
    """Removes the state from a team name"""
    name = re.sub(r'\b%s$' % re.escape(state), '', name)
    name = re_strip(name)
    return name

def is_same_base_team(loteca_team, betexp_team, countries):
    if not (loteca_team.tokens.country or loteca_team.tokens.state):
        # country team
        fname = loteca_team.fname
        translation = countries[fname]
        return betexp_team.fname == translation
    elif loteca_team.tokens.state:
        # brazilian team
        if loteca_team.tokens.state == betexp_team.tokens.state:
            loteca_fname = remove_state_from_name(loteca_team.fname, loteca_team.tokens.state)
            betexp_fname = remove_state_from_name(betexp_team.fname, betexp_team.tokens.state)
            return loteca_fname == betexp_fname
        else:
            return False
    else:
        # international team
        return (betexp_team.tokens.state is None) and \
                    (loteca_team.fname == betexp_team.fname)

def create_whole_dict(in_betexp_db, in_loteca_matches,
        in_countries_en, in_countries_ptbr, start_round=366):
    """Maps Loteca team strings into BetExplorer team strings

    This function first retrieve the matches for each source and then compares
    them, all of them against each other. Expect a long processing time.

    Args:
        in_betexp_db: BetExplorer database location (sqlite3)
        in_loteca_matches: Loteca matches location (pkl -> DataFrame)
        in_countries_en: countries dictionary in english (json)
        in_countries_ptbr: countries_dictionary in portugues (json)
        start_round: the first Loteca round to retrieve teams from

    Note:
        For the countries dictionaries, get more information at country.py

    Returns:
        A dictionary that maps (Loteca team string -> set of possible
        BetExplorer team strings). A warning is raised if one Loteca team
        corresponds to more than one BetExplorer team, but the result is saved.
    """
    # prepare data
    betexp_teams = betexplorer.retrieve_teams(in_betexp_db)
    loteca_teams = loteca.retrieve_teams(in_loteca_matches, start_round=start_round)
    countries = country.make_translations(in_countries_en, in_countries_ptbr)

    # core
    dict = defaultdict(set)
    for loteca_team in loteca_teams:
        loteca_string = loteca_team.string
        for betexp_team in betexp_teams:
            if is_same_base_team(loteca_team, betexp_team, countries):
                betexp_string = betexplorer.generate_string(betexp_team.name, loteca_team.tokens)
                dict[loteca_string].add(betexp_string)

        # log
        found_strings = dict[loteca_string]
        if len(found_strings) == 0:
            logger.info('"%s" -> NOTFOUND' % loteca_string)
        elif len(found_strings) == 1:
            logger.info('"%s" -> "%s"' % (loteca_string, next(iter(found_strings))))
        else:
            logger.warning('"%s" -> %s' % (loteca_string, list(found_strings)))

    return dict



# CLI

@click.command()
@click.argument('in-betexp-db', type=click.Path(exists=True))
@click.argument('in-loteca-matches', type=click.Path(exists=True))
@click.argument('in-countries-en', type=click.Path(exists=True))
@click.argument('in-countries-ptbr', type=click.Path(exists=True))
@click.argument('out-loteca-to-betexp', type=click.Path(writable=True))
@click.option('--start-round', default=366)
@click_log.simple_verbosity_option(logger, default='WARNING')
def CLI(in_betexp_db, in_loteca_matches, in_countries_en, in_countries_ptbr,
        out_loteca_to_betexp, start_round):
    """Creates and saves a dictionary that maps Loteca strings into BetExplorer
    strings. The BetExplorer strings are saved in a set (that way we can handle
    the cases where no strings were found or where multiple strings were found).

    Logger will message (INFO) all the strings that were found or not found.
    When more than one string is found, the logger will issue a WARNING.

    \b
    Inputs:
        betexp-db (sqlite3): the BetExplorer database file
        Loteca-matches (pkl): a DataFrame containing the Loteca matches
        in-countries-en (json): a file containing the list of countries (in
            english)
        in-countries-ptbr (json): a file containing the list of countries (in
            portuguese)
    
    \b
    Outputs:
        loteca-to-betexp (pkl): a dict containing the mapping (Loteca string ->
            set of possible BetExplorer strings). The BetExplorer strings don't
            have the country name attached to it, but have all the other tokens.

    \b
    Options:
        --start-round (int): the first Loteca round to retrieve matches from
        --verbosity (INFO or WARNING): the verbosity of the logger
    """

    dict = create_whole_dict(in_betexp_db, in_loteca_matches, in_countries_en, in_countries_ptbr, start_round=start_round)
    with open(out_loteca_to_betexp, mode='wb') as fp:
        pickle.dump(dict, fp)


if __name__ == '__main__':
    CLI()
