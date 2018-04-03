import pickle

import click
import pandas as pd


def extract_matches(rounds):
    """Extract matches for a given list of raw rounds

    Args:
        rounds: a list of rounds as retrieved directly from the loteca site

    Returns:
        A DataFrame containing the matches played in the rounds. The DataFrame
        has already been preprocessed, and can be used for further analysis.
    """
    # retrieve matches (while setting the 'concurso' value)
    matches = []
    for r in rounds:
        for m in r['jogos']:
            m['concurso'] = r['concurso']
            matches.append(m)

    # create DataFrame
    df = pd.DataFrame({
        'roundno': [m['concurso'] for m in matches],
        'gameno': [m['icJogo'] for m in matches],
        'teamH': [m['noTime1'] for m in matches],
        'teamA': [m['noTime2'] for m in matches],
        'goalsH': [m['qt_gol_time1'] for m in matches],
        'goalsA': [m['qt_gol_time2'] for m in matches],
        'date': [m['dt_jogo'] for m in matches]
    })

    # set columns type
    df['date'] = pd.to_datetime(df.date, unit='ms').dt.normalize()
    df['gameno'] = df.gameno.apply(int)
    df['goalsH'] = df.goalsH.apply(int)
    df['goalsA'] = df.goalsA.apply(int)

    # create 'happened' column
    df['happened'] = df.date.notnull()

    # order columns
    df = df[['roundno', 'gameno', 'date', 'teamH', 'goalsH', 'teamA', 'goalsA', 'happened']]

    # fix wrong dates
    old_dates = df.loc[df.roundno == 548, 'date']
    new_dates = old_dates.apply(lambda x: x.replace(month=3))
    df.loc[df.roundno == 548, 'date'] = new_dates

    return df


def _save_matches(in_loteca_site, out_lotecas_matches):
    with open(in_loteca_site, mode='rb') as fp:
        rounds = pickle.load(fp)

    matches = extract_matches(rounds)

    with open(out_lotecas_matches, mode='wb') as fp:
        pickle.dump(matches, fp)


# CLI

@click.command()
@click.argument('in-loteca-site', type=click.Path(exists=True))
@click.argument('out-lotecas-matches', type=click.Path(writable=True))
def save_matches(in_loteca_site, out_lotecas_matches):
    """Extract and save matches present in the raw data retrieved from the
    Loteca site. There's more info present in the said data, but, all that we
    care for now is this.

    \b
    Inputs:
        in-loteca-site (pkl): a file containing raw rounds extracted from the
            Loteca site

    \b
    Outputs:
        out-lotecas-matches (pkl): a DataFrame that contains all the matches
            played in the rounds from 'in-loteca-site'. The DataFrame has
            already been formatted and can be used without further processing.
    """
    _save_matches(in_loteca_site, out_lotecas_matches)


if __name__ == '__main__':
    save_matches()
