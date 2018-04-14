import logging
import sqlite3
from collections import defaultdict, namedtuple
from datetime import date, timedelta

import click
import pandas as pd

from src.data.interim.teams import betexplorer, loteca
from src.util import load_pickle, re_split, save_pickle


# Match used in the algorithm below
# id = (DataFrame index - Loteca) | (identifier from site - BetExplorer)
# date = python date object
# h = Home
# a = Away
# th = Team Home
# ta = Team Away
fields = ('id '
          'date '
          'score_h score_a '
          'th_string ta_string '
          'th_fname ta_fname '
          'th_under ta_under '
          'th_women_flag ta_women_flag')

Match = namedtuple('Match', fields)


def identity(t1, t2):
    return t1 == t2


def is_same_match(lt_match, be_match,
                  teams_fn=identity,
                  needed_teams=2):
    """Determine if two matches are the same

    We assume the date and score have already been checked.
    """
    lt = lt_match
    be = be_match

    # basic team
    if (lt.th_women_flag != be.th_women_flag or
          lt.ta_women_flag != be.ta_women_flag or
          lt.th_under != be.th_under or
          lt.ta_under != be.ta_under):
        return False

    # teams
    if needed_teams == 2:
        return (teams_fn(lt.th_fname, be.th_fname) and
                teams_fn(lt.ta_fname, be.ta_fname))
    elif needed_teams == 1:
        return (teams_fn(lt.th_fname, be.th_fname) or
                teams_fn(lt.ta_fname, be.ta_fname))
    else:
        return True


def generate_reverse(matches):
    """Generate a dictionary that maps scores/dates into matches

    The resulting dictionary will be of the following form:
        'scores':
            (0,0): set(index of matches with (0,0) score)
            (0,1): set(index of matches with (0,1) score)
            ...
        'dates':
            date(2009-12-31): set(index of matches in the given date)
            ...
    """
    dates = defaultdict(set)
    scores = defaultdict(set)
    for i, m in enumerate(matches):
        dates[m.date].add(i)
        scores[(m.score_h, m.score_a)].add(i)

    return {'scores': scores, 'dates': dates}


def filter_matches(loteca_match, betexp_matches, kwargs, reverse_dict):
    """Filter BetExplorer matches

    In the kwargs, we expect two arguments:

        score_tolerance: Maximum difference in goals between 2 matches so that
            they can be considered the same. Defaults to 0.

        date_tolerance: Maximum difference in dates between 2 matches so that
            they can be considered the same. Defaults to 0 (dates must be the
            same).
    """
    score_indexes = set()
    score_tolerance = kwargs.get('score_tolerance', 0)
    for score, indexes in reverse_dict['scores'].items():
        score_diff = (abs(loteca_match.score_h - score[0]) +
                        abs(loteca_match.score_a - score[1]))
        if score_diff <= score_tolerance:
            score_indexes |= indexes

    date_indexes = set()
    date_tolerance = kwargs.get('date_tolerance', timedelta())
    for date, indexes in reverse_dict['dates'].items():
        date_diff = abs(loteca_match.date - date)
        if date_diff <= date_tolerance:
            date_indexes |= indexes

    intersect_indexes = score_indexes & date_indexes
    filtered = [m for i, m in enumerate(betexp_matches)
                if i in intersect_indexes]

    return filtered


def generate_ltb_matches_dict(loteca_matches, betexp_matches, teamsd):
    # logging
    def format_match(match):
        date_str = match.date.strftime('%d-%m-%y')
        s = "{date} {th} {sh}x{sa} {ta}"
        s = s.format(date=date_str,
                     th=match.th_string,
                     ta=match.ta_string,
                     sh=match.score_h,
                     sa=match.score_a)
        return s

    def log_team(lt_fname, be_fname):
        msg = "TEAM {lt_fname:>{lt_max}} -> {be_fname}"
        msg = msg.format(lt_fname=lt_fname,
                         be_fname=be_fname,
                         lt_max=LOTECA_MAX_TEAM)
        logging.info(msg)

    def log_match(lt_match, be_matches):
        msg = "MATCH {lt_match:>{lt_max_match}} -> {be_matches}"
        msg = msg.format(lt_match=format_match(lt_match),
                         be_matches=[format_match(m) for m in be_matches],
                         lt_max_match=LOTECA_MAX_MATCH)
        log_level = logging.INFO if len(be_matches) <= 1 else logging.ERROR
        logging.log(log_level, msg)

    # fname comparison functions
    def compare_teams_rigid(lt_team, be_team):
        return be_team in teamsd[lt_team]

    def compare_teams_flex(team1, team2):
        pieces1 = [p for p in re_split(team1) if len(p) > 2]
        pieces2 = [p for p in re_split(team2) if len(p) > 2]
        return (pieces1 == pieces2 or
                  pieces1 < pieces2 or
                  pieces2 < pieces1)

    LOTECA_MAX_TEAM = max(len(n) for n in teamsd)
    LOTECA_MAX_MATCH = max(len(format_match(m)) for m in loteca_matches)

    # core
    reverse_dict = generate_reverse(betexp_matches)

    param_set = [
        (
            'Link certain matches',
             {'teams_fn': compare_teams_rigid}
        ),
    ]

    ltb_dict = {}
    for msg, kwargs in param_set:
        logging.info(msg)
        for loteca_match in loteca_matches:

            filtered_matches = filter_matches(
                    loteca_match, betexp_matches, kwargs, reverse_dict)
            matching = [m for m in filtered_matches if is_same_match(loteca_match, m, **kwargs)]
            log_match(loteca_match, matching)

            # we only save results when there
            # is exactly one matching
            if len(matching) == 1:
                # update matches dict
                betexp_match = matching.pop()
                ltb_dict[loteca_match.id] = betexp_match.id

                # update teams dict
                lt_th = loteca_match.th_fname
                lt_ta = loteca_match.ta_fname
                be_th = betexp_match.th_fname
                be_ta = betexp_match.ta_fname

                if be_th not in teamsd[lt_th]:
                    teamsd[lt_th].add(be_th)
                    log_team(lt_th, be_th)

                if be_ta not in teamsd[lt_ta]:
                    teamsd[lt_ta].add(be_ta)
                    log_team(lt_ta, be_ta)
        else:
            loteca_matches = [m for m in loteca_matches if m.id not in ltb_dict]

    return ltb_dict


def get_loteca_match(row):
    """Generate a loteca Match from a row
    """
    th_name, th_under, th_women_flag, _, _ = loteca.parse_string(row.team_h)
    ta_name, ta_under, ta_women_flag, _, _ = loteca.parse_string(row.team_a)

    th_fname = loteca.format_name(th_name)
    ta_fname = loteca.format_name(ta_name)

    return Match(row.name,
                 row.date.to_pydatetime().date(),
                 row.goals_h, row.goals_a,
                 row.team_h, row.team_a,
                 th_fname, ta_fname,
                 th_under, ta_under,
                 th_women_flag, ta_women_flag)


def load_loteca_matches(in_loteca_matches):
    """Load and prepare loteca matches

    Only matches that happened will be retrieved.

    Output format is a list of Match objects.
    """
    df = load_pickle(in_loteca_matches)
    matches = [get_loteca_match(row)
               for id, row in df.iterrows()
               if row.happened]
    return matches


def load_betexp_matches(in_betexp_db):
    """Load and prepare BetExplorer matches

    Output format is a list of Match objects.

    Matches without score are ignored.
    """
    # load database rows into DataFrame
    conn = sqlite3.connect(in_betexp_db)
    q = "SELECT id, date, team_h, team_a, score FROM betexp_matches"
    df = pd.read_sql_query(q, conn)
    conn.close()

    # remove duplicates
    # these are real duplicates that were caused
    # by the way BetExplorer organize its matches
    df = df.drop_duplicates(subset='id')

    # prepare data
    def get_date(s):
        d, m, y = [int(v) for v in s.split('.')]
        global date
        return date(y, m, d)

    def get_score(s):
        if s == '':
            return None

        s = s.strip()
        return [int(v) for v in s.split(':')]

    def process_name(s):
        name, _, women_flag, under, _ = betexplorer.parse_string(s)
        fname = betexplorer.format_name(name)
        return (s, fname, under, women_flag)

    dates = [get_date(s) for s in df.date]
    scores = [get_score(s) for s in df.score]
    h_names = [process_name(s) for s in df.team_h]  # about 10us per entry
    a_names = [process_name(s) for s in df.team_a]

    # create Match objects
    matches = []
    for idd, date, score, h_name, a_name in zip(
            df.index, dates, scores, h_names, a_names):
        if score:
            match = Match(
                idd,
                date,
                score[0], score[1],
                h_name[0], a_name[0],
                h_name[1], a_name[1],
                h_name[2], a_name[2],
                h_name[3], a_name[3])
            matches.append(match)
    return matches


@click.command()
@click.argument('in-loteca-matches', type=click.Path(exists=True))
@click.argument('in-betexp-db', type=click.Path(exists=True))
@click.argument('in-ltb-teams', type=click.Path(exists=True))
@click.argument('out-ltb-matches', type=click.Path(writable=True))
def CLI(in_loteca_matches, in_betexp_db, in_ltb_teams, out_ltb_matches):
    """Links Loteca matches into betExplorer matches

    \b
    Inputs:
        loteca-matches (pkl): A DataFrame containing processed loteca matches.
        betexp-db (sqlite3): A database containing BetExplorer matches.
        ltb-teams (pkl) A dictionary mapping Loteca teams fnames into
            BetExplorer teams fnames.

    \b
    Outputs:
        ltb-matches (pkl): A dicionary mapping Loteca matches ids into
            BetExplorer matches ids.
    """
    logging.getLogger().setLevel(logging.INFO)  # TODO
    logging.info("Loading data...")
    loteca_matches = load_loteca_matches(in_loteca_matches)
    betexp_matches = load_betexp_matches(in_betexp_db)
    ltb_teams = load_pickle(in_ltb_teams)

    logging.info("Matching loteca matches into BetExplorer ones...")
    ltb_matches = generate_ltb_matches_dict(loteca_matches, betexp_matches, ltb_teams)

    logging.info("Saving...")
    save_pickle(out_ltb_matches, ltb_matches)


if __name__ == '__main__':
    CLI()
