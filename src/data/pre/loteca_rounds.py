import pickle

import click
import pandas as pd
import parsel


def _read_int(x):
    try:
        return int(x)
    except TypeError:
        return


def _read_float(x):
        if x == ' - ':
            return None
        return float(x.replace('.', '').replace(',', '.'))


def extract_df(in_loteca_htm):
    """Preprocess the data in the loteca file

    Returns:
        A DataFrame with all the rounds present in the Loteca file
    """
    # load file

    with open(in_loteca_htm, mode='rb') as fp:
        body = fp.read()
        body = body.decode('windows-1252')
    selector = parsel.Selector(body)

    # core
    rows = selector.css('tr')
    header = rows[0]
    rows = rows[1:]
    columns = header.css('font::text').extract()

    rounds = []
    for row in rows:
        tds = row.css('td')
        td_cnt = len(tds)
        if td_cnt == 28:
            # round row
            data = [td.css('::text').extract_first() for td in tds]
            rounds.append(data)
        elif td_cnt == 2:
            # state row
            continue
        else:
            raise ValueError("Loteca file row with different number of cells")

    # create DataFrame
    df = pd.DataFrame.from_records(rounds, columns=columns)

    # remove columns
    df = df.drop(['Cidade', 'UF'], axis=1)
    df = df.drop(['Jogo_%s' % i for i in range(1, 15)], axis=1)

    # rename columns
    df.columns = ['roundno', 'date', 'winners14', 'shared14', 'accumulated',
                  'accumulated14', 'winners13', 'shared13', 'winners12',
                  'shared12', 'total_revenue', 'prize_estimative']

    # convert types
    df['roundno'] = df.roundno.apply(_read_int)
    df['date'] = pd.to_datetime(df.date, dayfirst=True)
    df['winners14'] = df.winners14.apply(_read_int)
    df['winners13'] = df.winners13.apply(_read_int)
    df['winners12'] = df.winners12.apply(_read_int)
    df['shared14'] = df.shared14.apply(_read_float)
    df['shared13'] = df.shared13.apply(_read_float)
    df['shared12'] = df.shared12.apply(_read_float)
    df['accumulated'] = df.accumulated.apply(lambda x: x == 'SIM')
    df['accumulated14'] = df.accumulated14.apply(_read_float)
    df['total_revenue'] = df.total_revenue.apply(_read_float)
    df['prize_estimative'] = df.prize_estimative.apply(_read_float)

    # set index
    df = df.set_index('roundno')

    return df


# CLI

@click.command()
@click.argument('in-loteca-htm', type=click.Path(exists=True))
@click.argument('out-loteca-rounds', type=click.Path(writable=True))
def preprocess_file(in_loteca_htm, out_loteca_rounds):
    """Preprocess the data in the loteca file, extracting rounds.

    \b
    Inputs:
        in-loteca-htm (htm): the raw loteca.htm file

    \b
    Outputs:
        out-loteca-rounds (pkl): contains a DataFrame with all the loteca rounds
    """
    # extract
    df = extract_df(in_loteca_htm)

    # save
    with open(out_loteca_rounds, mode='wb') as fp:
        pickle.dump(df, fp)


if __name__ == '__main__':
    preprocess_file()
