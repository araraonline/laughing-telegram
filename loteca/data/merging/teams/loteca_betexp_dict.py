"""In this file we will try to merge the loteca rounds with the BetExplorer
rounds. To do this, we split the data into three functional parts:
    
    - World Cup games (between countries)
    - International games (between international teams)
    - Brazilian games (between brazilian teams)

Each type of game has its own intricacies in the matter of processing team names
and some other stuff...

In the end, we expect a dictionary that connects the loteca matches IDs to the
BetExplorer matches IDs, in all categories. Matches that were not found should
have their dictionary value set to None.

Good luck!
"""
import logging
import pickle
import re
import sqlite3

import click
import click_log
import pandas as pd

import loteca.data.merging.teams.betexplorer as betexplorer
import loteca.data.merging.teams.loteca as loteca
from loteca.data.merging.teams.commons import FTeam


logger = logging.getLogger('loteca-betexp-dict')
click_log.basic_config(logger)



# Distance measures - if on team is contained in another, we return 0

def fteam_distance(fteam1, fteam2):
    fname1, fstate1 = fteam1
    fname2, fstate2 = fteam2

    return fname_distance(fname1, fname2) + (fstate1 != fstate2)

def fname_distance(fname1, fname2):
    blob1 = set(re.split(r'[^A-Za-z0-9]+', fname1))
    blob2 = set(re.split(r'[^A-Za-z0-9]+', fname2))

    return min(len(blob1 - blob2), len(blob2 - blob1))


# Core

def create_whole_dict(IN_LOTECA_MATCHES, IN_BETEXP_DB, IN_COUNTRIES_DICT, start_round=1):
    # get loteca team strings
    loteca_matches = pd.read_pickle(IN_LOTECA_MATCHES)
    loteca_matches = loteca_matches[loteca_matches.roundno >= start_round]
    loteca_strings = sorted(set(loteca_matches.teamH) | set(loteca_matches.teamA))

    # load loteca to betexplorer countries dict
    with open(IN_COUNTRIES_DICT, mode='rb') as fp:
        countries_dict = pickle.load(fp)

    # create BetExplorer dictionaries ([fteam OR fname] -> name)
    betexp_brazil_fteams = betexplorer.create_brazilian_fteam_dict(IN_BETEXP_DB)
    betexp_world_fnames = betexplorer.create_world_fname_dict(IN_BETEXP_DB)

    # core
    dict = {}
    for loteca_string in loteca_strings:
        # split loteca string parts
        loteca_name, state, tokens = loteca.split_string(loteca_string)
        loteca_fname = loteca.format_name(loteca_name)

        # retrieve betexplorer name (if clause)
        betexp_name = None        

        ## state == 'w' refers to matches between countries
        if state == 'w':
            betexp_fname = countries_dict[loteca_fname]
            betexp_name = betexp_world_fnames[betexp_fname]

        ## state = 'LL' (L = letter) refers to brazilian teams
        elif len(state) == 2:
            loteca_fteam = FTeam(loteca_fname, state)
            if loteca_fteam in betexp_brazil_fteams:
                betexp_fteam = loteca_fteam
                betexp_name = betexp_brazil_fteams[betexp_fteam]
            else:
                distances = [fteam_distance(loteca_fteam, betexp_fteam) for betexp_fteam in betexp_brazil_fteams]
                if distances.count(0) == 1:
                    betexp_fteam = list(betexp_brazil_fteams)[distances.index(0)]
                    betexp_name = betexp_brazil_fteams[betexp_fteam]
                    logger.info('Loteca to BetExp (distance): "{}" -> "{}"'.format(loteca_fteam, betexp_fteam))
                elif distances.count(0) > 1:
                    logger.warning('Multiple BetExplorer teams for: "{}"'.format(loteca_fteam))

        ## state == 'LLL' (L = letter) refers to international teams
        elif len(state) == 3:
            if loteca_fname in betexp_world_fnames:
                betexp_fname = loteca_fname
                betexp_name = betexp_world_fnames[betexp_fname]
            else:
                distances = [fname_distance(loteca_fname, betexp_fname) for betexp_fname in betexp_world_fnames]
                if distances.count(0) == 1:
                    betexp_fname = list(betexp_world_fnames)[distances.index(0)]
                    betexp_name = betexp_world_fnames[betexp_fname]
                    logger.info('Loteca to BetExp (distance): "{}" -> "{}"'.format(loteca_fname, betexp_fname))
                elif distances.count(0) > 1:
                    fteams = [list(betexp_world_fnames)[i] for i, dist in enumerate(distances) if dist == 0]
                    logger.warning('Multiple BetExplorer teams for: "{}"'.format(loteca_fname))

        ## states should be 1, 2 or 3 characters long
        else:
            raise ValueError('Got weird State for string "{}": "{}"'.format(loteca_string, state))

        # generate BetExplorer string
        if betexp_name:
            betexp_string = betexplorer.generate_string(betexp_name, tokens)
            logger.debug('Loteca to BetExp: "{}" -> "{}"'.format(loteca_string, betexp_string))
        else:
            betexp_string = None
            logger.debug('Loteca to BetExp: "{}" -> NOT FOUND'.format(loteca_string))

        # save result to dict
        dict[loteca_string] = betexp_string

    return dict


# CLI

@click.command()
@click.argument('in-loteca-matches', type=click.Path(exists=True))
@click.argument('in-betexp-db', type=click.Path(exists=True))
@click.argument('in-countries-dict', type=click.Path(exists=True))
@click.argument('out-loteca-to-betexp-dict', type=click.Path(writable=True))
@click.option('--start-round', default=366)
@click_log.simple_verbosity_option(logger, default='WARNING')
def CLI(in_loteca_matches, in_betexp_db,
        in_countries_dict, out_loteca_to_betexp_dict,
        start_round):
    """Creates a dictionary that maps Loteca strings into BetExplorer strings.
    It does so by some complicated logic that can be found in the
    create_whole_dicreate_whole_dict() function.

    Loteca strings whose counterpart were not found have their dictionary value
    set to None.

    \b
    Note:
        This function is very prone to failure, so, make sure to revisit it
        later and update some values manually after you use the dict to merge
        the matches.

    \b
    Args:
        in-loteca-matches: the location of the .pkl file that contains the
            matches found in the loteca site
        in-betexp-db: the location of the database that contains the BetExplorer
            matches
        in-countries-dict: the location of the dictionary that will translate
            countries from portuguese to english
       out-loteca-to-betexp-dict: the loction to save the resulting dictionary
           of this script

    \b
    Options:
        --start-round: the first loteca round to look for when searching for
            teams. Set as default to 366, as this is the first loteca round
            where we have revenue information.
    """
    dict = create_whole_dict(in_loteca_matches, in_betexp_db, in_countries_dict, start_round)
    with open(out_loteca_to_betexp_dict, mode='wb') as fp:
        pickle.dump(dict, fp)


if __name__ == '__main__':
    CLI()
