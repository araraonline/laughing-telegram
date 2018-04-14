import logging
import pickle
import re
import sqlite3
from collections import defaultdict, OrderedDict

import click
import click_log
import numpy as np
import pandas as pd

import src.data.interim.teams as teams


logger = logging.getLogger("loteca-betexp-matches-dict")
click_log.basic_config(logger)


MANUAL_TEAMS = {
    'ATLÉTICO MADRID/ESP' : {'Atl. Madrid'},
}


def compare_teams_rigid(team1, team2, teamsd):
    return team2 in teamsd.get(team1, set())


def compare_teams_flex(team1, team2):
    """Check if two teams are the same based on their names

    This function uses some heuristics to decide whether the teams are the same
    or not. Here's what it does:

    1. Extract the fname and tokens for both strings
    2. Check if both the teams have tokens for under a certain age. If one has
        it, the other must also have and the age must be the same.
    3. Check if the teams are women team. Men only play against men and women
        only play against women.
    4. Extract pieces of the formatted names and compare them. To compare, we
        check if one set of pieces is contained in another. If this is True,
        then, the teams are equal.

        Note: team pieces of 2 characters or less are ignored (we hope to
        exclude some of the 'FC's of 'EC's.

    Args:
        team1: Loteca team string
        team2: BetExplorer team string

    Returns:
        A boolean indicating whether team1 and team2 can be considered the same.
    """
    loteca_string = team1
    betexp_string = team2

    loteca_name, loteca_tokens = teams.loteca.extract_tokens(loteca_string)
    betexp_name, betexp_tokens = teams.betexplorer.extract_tokens(betexp_string)

    loteca_fname = teams.loteca.format_name(loteca_name)
    betexp_fname = teams.betexplorer.format_name(betexp_name)

    # rigid tests
    if loteca_tokens.under != betexp_tokens.under:
        return False
    if loteca_tokens.women != betexp_tokens.women:
        return False

    # fname comparison
    loteca_pieces = set([piece for piece in re.split(r'\W+', loteca_fname) if len(piece) > 2])
    betexp_pieces = set([piece for piece in re.split(r'\W+', betexp_fname) if len(piece) > 2])

    # both teams must have pieces
    if not loteca_pieces or not betexp_pieces:
        return False

    # A >= B means A contains every element of B
    return (loteca_pieces >= betexp_pieces) or (betexp_pieces >= loteca_pieces)


def generate_matches_dict(loteca_df, betexp_df, teamsd,
                          ignore_date=False,
                          flexible_date=False,
                          ignore_score=False,
                          min_team_rigid_points=2, min_team_flex_points=2,
                          return_teams=False,
                          logger=logger):
    """Generates a dictionary matching Loteca and BetExplorer matches. This may
    be quite slow depending on the inputs. So, iterate wisely.

    Note:
        Be careful with games that didn't happen, as these don't have dates. Set
        ignore_date=True when dealing with those.

    Args:
        loteca_df: DataFrame containing the Loteca matches you wanna create
            links from. All of the matches here are used to generate links.
        betexp_df: DataFrame containing the matches from BetExplorer. Along with
            the usual columns.
        teamsd: a dictionary mapping (Loteca team fname -> BetExplorer team
            fname). This is generated in the folder 'loteca/data/interim/teams/'
        ignore_date: a boolean indicating whether or not we should ignore the
            date.
        flexible_date: a boolean indicating whether to use flexible dates when
            comparing matches. False means the dates must be exactly equal. True
            means the dates can be 1 day away from each other.
        ignore_score: if set to True, the scores of the matches are ignored.
        min_team_rigid_points: when comparing matches from Loteca to BetExplorer,
            minimum amount of teams that must have a mapping in the `teamsd`
            dictionary so that the matches can be considered the same. Set it to
            either 0, 1 or 2.
        min_team_flex_points: when comparing matches from Loteca to BetExplorer,
            minimum amount of teams that can be softly linked to consider the
            matches equal. Set it to either 0, 1 or 2. Team links present in the
            `teamsd` dict also count towards flex team points.
        return_teams: if True, returns a dictionary of the new teams discovered,
            along with the original matches dict.
        logger: the logger to be used.

    Returns:
        A dictionary that maps (Loteca match ID -> BetExplorer match id).

        If return_teams is set to True, the function will return a tuple
        (matches dict, new teams dict). Matches dict is the dictionary referred
        above. New teams dict is a dictionary that maps (Loteca team string ->
        set of BetExplorer team strings) for teams that have no translation in
        teamsd yet.
    """
    ret = OrderedDict()  # good for debugging
    newteams = defaultdict(set)

    assert min_team_flex_points >= min_team_rigid_points  # just some sanity checking

    logger.info("-----")
    logger.info("Generating matches dict...")
    logger.info("There are {} loteca matches to find".format(loteca_df.shape[0]))
    logger.info("ignore_date={}".format(ignore_date))
    logger.info("flexible_date={}".format(flexible_date))
    logger.info("ignore_score={}".format(ignore_score))
    logger.info("min_team_rigid_points={}".format(min_team_rigid_points))
    logger.info("min_team_flex_points={}".format(min_team_flex_points))

    # create set of possible matches

    # restrict teams
    if min_team_rigid_points > 0:
        rigid_teams = set()
        for value in teamsd.values():
            rigid_teams |= value

        if min_team_rigid_points == 1:
            # at least one team must be in the teamd values
            betexp_df = betexp_df[betexp_df.team_h.isin(rigid_teams) |
                                  betexp_df.team_a.isin(rigid_teams)]
        else:
            # both teams must be in the teamd values
            betexp_df = betexp_df[betexp_df.team_h.isin(rigid_teams) &
                                  betexp_df.team_a.isin(rigid_teams)]

    # cache DataFrames of retricted dates (to speed up)
    if not ignore_date:
        date_to_df = {}
        for date in set(loteca_df.date):
            if flexible_date:
                date_to_df[date] = betexp_df[abs(betexp_df.date - date) <= pd.Timedelta(days=1)]
            else:
                date_to_df[date] = betexp_df[betexp_df.date == date]

    # core
    for i, (loteca_id, loteca_row) in enumerate(loteca_df.iterrows()):
        row = loteca_row

        # log
        if i % 500 == 0:
            logger.info("on match %s/%s" % (i + 1, loteca_df.shape[0]))

        # filter date
        if not ignore_date:
            choices = date_to_df[row.date]
        else:
            choices = betexp_df

        # filter score
        if not ignore_score:
            choices = choices[(choices.goals_h == row.goals_h) &
                              (choices.goals_a == row.goals_a)]

        # filter teams
        tokeep = []  # list of rows indexes to keep
        for choices_index, choices_row in choices.iterrows():
            # get points for home team
            rigid_h = compare_teams_rigid(loteca_row.team_h, choices_row.team_h, teamsd)
            flex_h = True if rigid_h else compare_teams_flex(loteca_row.team_h, choices_row.team_h)

            # get points for away team
            rigid_a = compare_teams_rigid(loteca_row.team_a, choices_row.team_a, teamsd)
            flex_a = True if rigid_a else compare_teams_flex(loteca_row.team_a, choices_row.team_a)

            # sum points
            rigid_points = rigid_h + rigid_a
            flex_points = flex_h + flex_a

            # save
            if rigid_points >= min_team_rigid_points and \
                    flex_points >= min_team_flex_points:
                tokeep.append(choices_index)
        choices = choices.loc[tokeep, :]

        # if we have only one choice left, then it's success
        choicecnt = choices.shape[0]
        if choicecnt == 0:
            logger.debug("%s -> NOT FOUND" % loteca_id)
            continue
        elif choicecnt == 1:
            betexp_id = choices.id.iloc[0]
            ret[loteca_id] = betexp_id

            if choices.team_h.iloc[0] not in teamsd[row.team_h]:
                newteams[row.team_h].add(choices.team_h.iloc[0])
            if choices.team_a.iloc[0] not in teamsd[row.team_a]:
                newteams[row.team_a].add(choices.team_a.iloc[0])

            logger.debug("#%s -> %s" % (loteca_id, betexp_id))
            continue
        else:
            betexp_ids = choices.id.tolist()
            logger.warning("%s -> %s" % (loteca_id, betexp_ids))
            continue

    logger.info("%s matches linked" % len(ret))
    logger.info("%s teams found:" % len(newteams))
    logger.info("{}".format(newteams))
    logger.info("-----")

    return (ret, newteams) if return_teams else ret


def generate_whole_matches_dict(loteca_df, betexp_df, teamsd, logger=logger):
    """Generate a dict linking Loteca matches to BetExplorer matches through
    various iterations.

    This function will call generate_matches_dict() a lot of times. At each
    call, the amount of matches we are searching gets lower, but, we give more
    freedom in how two matches are linked.

    Args:
        loteca_df: DataFrame containing the Loteca matches you wanna create
            links from. All of the matches here are used to generate links.
        betexp_df: DataFrame containing the matches from BetExplorer. Along with
            the usual columns.
        teamsd: a dictionary mapping (Loteca team fname -> BetExplorer team
            fname). This is generated in the folder 'loteca/data/interim/teams/'
        logger: the logger to be used. Defaults to the logger defined in this
            module.

    Returns:
        An OrderedDict that maps (Loteca match ID -> BetExplorer match ID).
    """
    ret = OrderedDict()

    loteca = loteca_df.copy()
    betexp = betexp_df.copy()
    teamsd = teamsd.copy()

    loteca0 = loteca[~loteca.happened]  # games that didn't happen
    loteca1 = loteca[loteca.happened]  # games that happened

    #### PREPROCESS TEAMS DICT

    MANUAL_TEAMS = {
        'ATLÉTICO MADRID/ESP' : {'Atl. Madrid'},
    }
    for k, v in MANUAL_TEAMS.items(): teamsd[k] |= v

    #### MAKE ITERATIONS (for games that happened)

    # Link matches we are sure
    logger.info("Link matches that we are sure - 1 iteration")
    # (close date) (same score) (2 teams the same)*
    df = loteca1
    results = generate_matches_dict(df, betexp, teamsd, logger=logger,
                                    flexible_date=True,
                                    min_team_rigid_points=2,
                                    min_team_flex_points=2,
                                    return_teams=False)
    ret.update(results)

    # Discover some new teams
    logger.info("Discover some new teams - 3 iterations")
    # (close date) (same score) (1 team the same) (other team alike)*
    df = df[~df.index.isin(ret)]
    results, newteams = generate_matches_dict(df, betexp, teamsd, logger=logger,
                                              flexible_date=True,
                                              min_team_rigid_points=1,
                                              min_team_flex_points=2,
                                              return_teams=True)
    for k, v in newteams.items(): teamsd[k] |= v
    ret.update(results)

    # Discover some new teams
    # (close date) (same score) (1 team the same) (other team whatever)*
    df = df[~df.index.isin(ret)]
    results, newteams = generate_matches_dict(df, betexp, teamsd, logger=logger,
                                              flexible_date=True,
                                              min_team_rigid_points=1,
                                              min_team_flex_points=1,
                                              return_teams=True)
    for k, v in newteams.items(): teamsd[k] |= v
    ret.update(results)

    # Discover some new teams
    # (close date) (same score) (2 teams alike)*
    df = df[~df.index.isin(ret)]
    results, newteams = generate_matches_dict(df, betexp, teamsd, logger=logger,
                                              flexible_date=True,
                                              min_team_rigid_points=0,
                                              min_team_flex_points=2,
                                              return_teams=True)
    for k, v in newteams.items(): teamsd[k] |= v
    ret.update(results)

    # Discover some new scores
    logger.info("Discover some new scores - 2 iterations")
    # (close date) (different score) (2 teams the same)
    df = df[~df.index.isin(ret)]
    results, newteams = generate_matches_dict(df, betexp, teamsd, logger=logger,
                                              flexible_date=True,
                                              min_team_rigid_points=2,
                                              min_team_flex_points=2,
                                              ignore_score=True,
                                              return_teams=True)
    for k, v in newteams.items(): teamsd[k] |= v
    ret.update(results)

    # Discover some new scores
    # (close date) (different score) (2 teams alike)
    df = df[~df.index.isin(ret)]
    results, newteams = generate_matches_dict(df, betexp, teamsd, logger=logger,
                                              flexible_date=True,
                                              min_team_rigid_points=0,
                                              min_team_flex_points=2,
                                              ignore_score=True,
                                              return_teams=True)
    for k, v in newteams.items(): teamsd[k] |= v
    ret.update(results)

    # if we try only 1 team alike we get loads of bad results

    # #### MAKE ITERATIONS (for games that didn't happen)
    # # From now on we are ignoring matches that didn't happen
    # # Ignoring the date AND the score is one of the best recipes
    # # For false positives
    #
    # logger.info("Discover matches that didn't happen - 1 iteration")
    # df1 = loteca0
    # df2 = betexp[betexp.scoremod.isin(['ABN.', 'AWA.', 'CAN.', 'INT.', 'POSTP.', 'WO.'])]
    # results, newteams = generate_matches_dict(df1, df2, teamsd, logger=logger,
    #                                           ignore_date=True,
    #                                           ignore_score=True,
    #                                           min_team_rigid_points=2,
    #                                           min_team_flex_points=2,
    #                                           return_teams=True)
    # for k, v in newteams.items(): teamsd[k] |= v
    # ret.update(results)

    return ret


@click.command()
@click.argument('in-loteca-matches', type=click.Path(exists=True))
@click.argument('in-betexp-db', type=click.Path(exists=True))
@click.argument('in-teams-dict', type=click.Path(exists=True))
@click.argument('out-matches-dict', type=click.Path(writable=True))
@click.option('--start-round', default=366)
@click_log.simple_verbosity_option(logger=logger, default='INFO')
def save_whole_matches_dict(in_loteca_matches, in_betexp_db, in_teams_dict,
                            out_matches_dict, start_round):
    """Create and save a mapping that links Loteca matches into BetExplorer
    matches.

    This is made by iterating over the Loteca matches and finding those in the
    BetExplorer database that are equivalent. If there's only one BetExplorer
    equivalent for a Loteca match, we stabilish a link.

    This process is repeated various times, each time with a different
    prerequisite to consider two matches the same. During the process, we also
    discover some teams that should be linked, and we log those as an INFO.

    The process is quite long, so be sure to be patient, and not to run this
    unless it is necessary.

    \b
    Inputs:
        loteca-matches (pkl): a DataFrame containing matches that came from the
            Loteca site.
        betexp-db (sqlite3): the BetExplorer database, with all its matches.
        teams-dict (pkl): a dictionary that maps (Loteca team strings ->
            BetExplorer team strings). It was generated in the folder
            'loteca/data/interim/teams/'.

    \b
    Outputs:
        matches-dict (pkl): a dictionary that maps (Loteca match ID ->
            BetExplorer match ID). Here, the Loteca ID corresponds to the
            DataFrame index for the row and, the BetExplorer ID corresponds to
            the match ID that was provided by BetExplorer itself, as it is
            unique.

    \b
    Options:
        start-round (int): the first round from Loteca we want to link matches
            from. Defaults to 366 (the first round where we have money
            information).
        verbosity (DEBUG, INFO or WARNING): 'DEBUG' will show you all the
            linkings that are being made (they are a lot). 'INFO' will show you
            more general info, like the progress in the iterations. 'WARNING'
            will only show failed linkings (the ones where we find two
            BetExplorer matches for one Loteca match).
    """
    logger.info("Load files")

    # load loteca
    loteca = pd.read_pickle(in_loteca_matches)
    loteca = loteca[loteca.roundno >= start_round]  # exclude old rounds

    # load betexplorer
    conn = sqlite3.connect(in_betexp_db)
    betexp = pd.read_sql_query('SELECT id, league_category, date, team_h, team_a, score, scoremod FROM betexp_matches', conn)
    conn.close()

    # preprocess betexplorer
    betexp.date = pd.to_datetime(betexp.date, dayfirst=True)
    betexp.score = betexp.score.str.strip()
    betexp['goals_h'] = [int(score.split(':')[0]) if score else np.nan for score in betexp.score]
    betexp['goals_a'] = [int(score.split(':')[1]) if score else np.nan for score in betexp.score]

    # load teams dict
    with open(in_teams_dict, mode='rb') as fp:
        teamsd = pickle.load(fp)

    # generate matches dict
    logger.info("Generate Loteca to BetExplorer matches dictionary")
    result = generate_whole_matches_dict(loteca, betexp, teamsd)
    logger.info("Found {} out of {} matches".format(len(result), loteca.shape[0]))

    # save matches dict
    logger.info("Save dictionary")
    with open(out_matches_dict, mode='wb') as fp:
        pickle.dump(result, fp)


if __name__ == '__main__':
    save_whole_matches_dict()
