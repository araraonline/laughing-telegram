import pickle
import pandas as pd
import click

def get_rounds_df(rounds):
    df = pd.DataFrame({
        'roundno': [r['concurso'] for r in rounds],
        'date':    [r['dtApuracao'] for r in rounds],
        'note':    [r['de_observacao'] for r in rounds]
    })
    df['date'] = pd.to_datetime(df.date, unit='ms').dt.normalize()
    df = df.set_index('roundno')
    return df

def get_games_df(rounds):
    # extract games from rounds
    games = []
    for r in rounds:
        for g in r['jogos']:
            g['concurso'] = r['concurso']
            games.append(g)

    # create DataFrame
    df = pd.DataFrame({
        'roundno': [g['concurso'] for g in games],
        'gameno': [g['icJogo'] for g in games],
        'teamH': [g['noTime1'] for g in games],
        'teamA': [g['noTime2'] for g in games],
        'goalsH': [g['qt_gol_time1'] for g in games],
        'goalsA': [g['qt_gol_time2'] for g in games],
        'date': [g['dt_jogo'] for g in games]
    })
    df['date'] = pd.to_datetime(df.date, unit='ms').dt.normalize()
    df['gameno'] = df.gameno.apply(int)
    df['goalsH'] = df.goalsH.apply(int)
    df['goalsA'] = df.goalsA.apply(int)
    df['happened'] = df.date.notnull()

    # format
    df.index = range(1, len(games) + 1)
    df = df[['roundno', 'gameno', 'date', 'teamH', 'goalsH', 'teamA', 'goalsA', 'happened']]
    
    return df

def get_cities_df(rounds):
    # extract cities info from rounds
    cities = []
    for r in rounds:
        for c in r['ganhadoresPorUf']:
            cities.append(c)

    # create DataFrame
    df = pd.DataFrame({
        'roundno': [c['nuConcurso'] for c in cities],
        'UF': [c['sgUf'] for c in cities],
        'city': [c['noCidade'] for c in cities],
        'winnercnt': [c['qtGanhadores'] for c in cities]
    })
    df['roundno'] = df.roundno.apply(int)

    # format
    df.index = range(1, len(cities) + 1)
    df = df[['roundno', 'UF', 'city', 'winnercnt']]
    
    return df
    
@click.command()
@click.argument('source', type=click.Path(exists=True))
@click.argument('rounds_dest', type=click.Path(writable=True))
@click.argument('games_dest', type=click.Path(writable=True))
@click.argument('cities_dest', type=click.Path(writable=True))
def extract_json(source, rounds_dest, games_dest, cities_dest):
    with open(source, mode='rb') as fp:
        rounds = pickle.load(fp)
        
    rounds_df = get_rounds_df(rounds)
    games_df = get_games_df(rounds)
    cities_df = get_cities_df(rounds)
    
    rounds_df.to_pickle(rounds_dest)
    games_df.to_pickle(games_dest)
    cities_df.to_pickle(cities_dest)
    
    return 0


if __name__ == '__main__':
    extract_json()
