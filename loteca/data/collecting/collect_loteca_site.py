import click
import pickle
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


def requests_retry_session(**retry_kwargs):
    session = requests.Session()
    retry = Retry(**retry_kwargs)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

QUERY_URL = r'http://loterias.caixa.gov.br/wps/portal/!ut/p/a1/04_Sj9CPykssy0xPLMnMz0vMAfGjzOLNDH0MPAzcDbz8vTxNDRy9_Y2NQ13CDA3cDYEKIoEKnN0dPUzMfQwMDEwsjAw8XZw8XMwtfQ0MPM2I02-AAzgaENIfrh-FqsQ9wBmoxN_FydLAGAgNTKEK8DkRrACPGwpyQyMMMj0VAbNnwlU!/dl5/d5/L2dBISEvZ0FBIS9nQSEh/pw/Z7_HGK818G0KOCO10AFFGUTGU0004/res/id=buscaResultado/c=cacheLevelPage/=/?timestampAjax=1518194221050&concurso={}'

@click.command()
@click.argument('loteca_table_loc', type=click.Path(exists=True))
@click.argument('output_filename', type=click.Path(writable=True))
def collect_loteca_rounds(loteca_table_loc, output_filename):
    """This will collect all the important data from the rounds
    in the loteca site.
    
    It will try not to download rounds that have already been downloaded
    and only retrieve rounds until the last one that is found in the
    loteca_file_rounds.pkl file.

    Output must be a .pkl
    """

    # determine first round
    try:
        with open(output_filename, mode='rb') as fp:
            rounds = pickle.load(fp)
    except FileNotFoundError:
        first_round = 1
        rounds = []
    else:
        first_round = max([r['concurso'] for r in rounds]) + 1

    # determine last round
    with open(loteca_table_loc, mode='rb') as fp:
        df = pickle.load(fp)
    last_round = df.index[-1]

    # stop if up-to-date
    nrounds = last_round - first_round + 1
    if nrounds == 0:
        click.echo("All rounds are up-to-date!")
        return

    # collect rounds
    click.echo("There are {} rounds to collect ({} to {})".format(nrounds, first_round, last_round))
    for roundno in range(first_round, last_round + 1):
        click.echo("Retrieving round {}".format(roundno))
        session = requests_retry_session(connect=10, read=3, redirect=5, backoff_factor=0.3)
        response = session.get(QUERY_URL.format(roundno))
        round = response.json()
        rounds.append(round)
    
    # save rounds
    with open(output_filename, mode='wb') as fp:
        pickle.dump(rounds, fp)
    click.echo("Done!")

if __name__ == '__main__':
    collect_loteca_rounds()
