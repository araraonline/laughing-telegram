import pandas as pd
import numpy as np
import click


###############################
# calculate distributed prizes

CUTOFF = pd.to_datetime('2016-01-02')

def get_totalprize13(total_revenue, date):
    if date >= CUTOFF:
        return total_revenue * 0.393 * 0.7 * 0.15 / 1.045
    else:
        return total_revenue * 0.400 * 0.7 * 0.15 / 1.045
        
def get_totalprize14(total_revenue, acc, date):
    if date >= CUTOFF:
        return total_revenue * 0.393 * 0.7 * 0.70 / 1.045 + acc
    else:
        return total_revenue * 0.400 * 0.7 * 0.70 / 1.045 + acc

def get_accumulated05(total_revenue, date):
    if date >= CUTOFF:
        return total_revenue * 0.393 * 0.7 * 0.15 / 1.045
    else:
        return total_revenue * 0.400 * 0.7 * 0.15 / 1.045


##################################
# core

def process_loteca_rounds(df):
    # work with a copy
    df = df.copy()

    # only keep rounds that contain the revenue
    df = df[df.total_revenue.notnull()]

    # add the bet price to count the amount of bets made
    df['betprice'] = 0.5
    df.loc[df.date >= pd.to_datetime('2015-05-18'), 'betprice'] = 1.0

    # calculate amount of bets
    df['betcnt'] = df.total_revenue / df.betprice
    df['betcnt'] = df.betcnt.apply(int)

    # algorithm over the rows
    columns = ['acc13', 'acc14', 'acc05', 'total13', 'total14', 'totalacc']
    for column in columns:
        df[column] = np.nan

    for i in df.index:
        # last accumulated 14 rights
        try:
            lastacc13 = df.loc[i - 1, 'acc13']
        except KeyError:
            lastacc13 = np.nan
            
        # last accumulated 13 rights
        try:
            lastacc14 = df.loc[i - 1, 'acc14']
        except KeyError:
            lastacc14 = np.nan
            
        # accumulated for rounds ending in 0 or 5
        if i % 5 == 0:
            values = df.loc[i - 5: i - 1, 'acc05']
            if values.shape[0] == 5:
                lastacc05 = values.sum()
            else:
                lastacc05 = np.nan
        else:
            lastacc05 = 0.0
            
        # total accumulated (for this round)
        totalacc = lastacc13 + lastacc14 + lastacc05
        
        # calculate prizes and stuff
        total_revenue = df.loc[i, 'total_revenue']
        date = df.loc[i, 'date']
        total13 = get_totalprize13(total_revenue, date)
        total14 = get_totalprize14(total_revenue, totalacc, date)
        acc13 = total13 if df.loc[i, 'winners13'] == 0 else 0.0
        acc14 = total14 if df.loc[i, 'winners14'] == 0 else 0.0
        acc05 = get_accumulated05(total_revenue, date)
        
        # assign values
        df.loc[i, 'total13'] = total13
        df.loc[i, 'total14'] = total14    
        df.loc[i, 'totalacc'] = totalacc
        df.loc[i, 'acc13'] = acc13
        df.loc[i, 'acc14'] = acc14
        df.loc[i, 'acc05'] = acc05

    # only keep rounds where 'totalacc' is present
    df = df[df.totalacc.notnull()]

    return df


@click.command()
@click.argument('orig_path', type=click.Path(exists=True))
@click.argument('dest_path', type=click.Path(writable=True))
def save_processed_rounds(orig_path, dest_path):
    rounds = pd.read_pickle(orig_path)
    rounds = process_loteca_rounds(rounds)
    rounds.to_pickle(dest_path)


if __name__ == '__main__':
    save_processed_rounds()
