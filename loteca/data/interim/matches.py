import logging
import pickle
import re
import sqlite3
from collections import defaultdict, OrderedDict

import click_log
import pandas as pd

import loteca.data.interim.teams as teams


logger = logging.getLogger("loteca-betexp-matches-dict")
click_log.basic_config(logger)


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
                            flexible_date=False,
                            ignore_score=False, ignore_score_if_mod=False,
                            min_team_rigid_points=2, min_team_flex_points=2,
                            return_teams=False,
                            logger=logger):
    """Generates a dictionary matching Loteca and BetExplorer matches. This may
    be quite slow depending on the inputs. So, iterate wisely.

    Note:
        Be careful with games that didn't happen, as these don't have dates.
        We're going to have to implent something different for them later.

    Args:
        loteca_df: DataFrame containing the Loteca matches you wanna create
            links from. All of the matches here are used to generate links, so,
            be careful with matches that were cancelled.
        betexp_df: DataFrame containing the matches from BetExplorer. Along with
            the usual columns, remember to include the league_category, so, the
            match filter can work.
        teamsd: a dictionary mapping (Loteca team fname -> BetExplorer team
            fname). This is generated in the folder 'loteca/data/interim/teams/'
        flexible_date: a boolean indicating whether to use flexible dates when
            comparing matches. False means the dates must be exactly equal. True
            means the dates can be 1 day away from each other.
        ignore_score: if set to True, the scores of the matches are ignored.
        igonre_score_if_mod: if set to True, the scores of the matches are
            ignored when the column 'scoremod' in the BetExplorer DataFrame is
            equal to a value different then ''.
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
    original_betexp_df = betexp_df  # keep as a reminder

    assert min_team_flex_points >= min_team_rigid_points  # just some sanity checking

    # create set of possible matches

    # restrict teams
    if min_team_rigid_points > 0:
        rigid_teams = set()
        for value in teamsd.values():
            rigid_teams |= value

        if min_team_rigid_points == 1:
            # at least one team must be in the teamd values
            betexp_df = betexp_df[betexp_df.teamH.isin(rigid_teams) |
                                    betexp_df.teamA.isin(rigid_teams)]
        else:
            # both teams must be in the teamd values
            betexp_df = betexp_df[betexp_df.teamH.isin(rigid_teams) &
                                    betexp_df.teamA.isin(rigid_teams)]

    # log
    logger.debug("original betexplorer shape: %s %s" % original_betexp_df.shape)
    logger.debug("restricted betexplorer shape: %s %s" % betexp_df.shape)

    # cache DataFrames of retricted dates (to speed up)
    logger.info("creating dataframe cache")
    date_to_df = {}
    for date in set(loteca_df.date):
        if flexible_date:
            date_to_df[date] = betexp_df[abs(betexp_df.date - date) <= pd.Timedelta(days=1)]
        else:
            date_to_df[date] = betexp_df[betexp_df.date == date]

    # core
    for i, (loteca_id, loteca_row) in enumerate(loteca_df.iterrows()):
        row = loteca_row
        choices = date_to_df[row.date]

        # log
        if i % 500 == 0:
            logger.info("on match %s/%s" % (i + 1, loteca_df.shape[0]))
        
        # filter score
        if not ignore_score:
            if ignore_score_if_mod:
                choices = choices[(choices.scoremod != '') | 
                                    ((choices.goalsH == row.goalsH) & 
                                        (choices.goalsA == row.goalsA))]
            else:
                choices = choices[(choices.goalsH == row.goalsH) &
                                    (choices.goalsA == row.goalsA)]

        # filter teams
        tokeep = []  # list of rows indexes to keep
        for choices_index, choices_row in choices.iterrows():
            # get points for home team
            rigidH = compare_teams_rigid(loteca_row.teamH, choices_row.teamH, teamsd)
            flexH = True if rigidH else compare_teams_flex(loteca_row.teamH, choices_row.teamH)

            # get points for away team
            rigidA = compare_teams_rigid(loteca_row.teamA, choices_row.teamA, teamsd)
            flexA = True if rigidA else compare_teams_flex(loteca_row.teamA, choices_row.teamA)

            # sum points
            rigid_points = rigidH + rigidA
            flex_points = flexH + flexA

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

            if choices.teamH.iloc[0] not in teamsd[row.teamH]:
                newteams[row.teamH].add(choices.teamH.iloc[0])
            if choices.teamA.iloc[0] not in teamsd[row.teamA]:
                newteams[row.teamA].add(choices.teamA.iloc[0])

            logger.debug("#%s -> %s" % (loteca_id, betexp_id))
            continue
        else:
            betexp_ids = choices.id.tolist()
            logger.warning("%s -> %s" % (loteca_id, betexp_ids))
            continue

    return (ret, newteams) if return_teams else ret


if __name__ == '__main__':
    logger.info("Link Loteca and BetExplorer matches")
    logger.info("Loading files")
    
    # load loteca
    loteca = pd.read_pickle('data/pre/lotecas_matches.pkl')
    loteca = loteca[loteca.roundno >= 366]  # exclude old rounds

    # load betexplorer
    conn = sqlite3.connect('../loteca/data/raw/betexplorer/db.sqlite3')
    betexp = pd.read_sql_query('SELECT id, league_category, date, teamH, teamA, score, scoremod FROM matches', conn)
    conn.close()

    betexp.date = pd.to_datetime(betexp.date, dayfirst=True)
    betexp.score = betexp.score.str.strip()
    betexp['goalsH'] = [int(score.split(':')[0]) if score else np.nan for score in betexp.score]
    betexp['goalsA'] = [int(score.split(':')[1]) if score else np.nan for score in betexp.score]

    # load dict
    with open('../data/interim/teams_ltb.pkl', mode='rb') as fp:
        teamsd = pickle.load(fp)
