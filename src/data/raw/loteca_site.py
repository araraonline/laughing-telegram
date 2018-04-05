import click

from src.data.raw.util import requests_retry_session
from src.util import load_pickle, save_pickle


FIRST_URL = r'http://loterias.caixa.gov.br/wps/portal/loterias/landing/loteca/!ut/p/a1/04_Sj9CPykssy0xPLMnMz0vMAfGjzOLNDH0MPAzcDbz8vTxNDRy9_Y2NQ13CDA3cDYEKIoEKnN0dPUzMfQwMDEwsjAw8XZw8XMwtfQ0MPM2I02-AAzgaENIfrh-FqsQ9wBmoxN_FydLAGAgNTKEK8DkRrACPGwpyQyMMMj0VAbNnwlU!/dl5/d5/L2dBISEvZ0FBIS9nQSEh/pw/Z7_HGK818G0KOCO10AFFGUTGU0004/res/id=buscaResultado/c=cacheLevelPage/=/?timestampAjax={}'
QUERY_URL = r'http://loterias.caixa.gov.br/wps/portal/!ut/p/a1/04_Sj9CPykssy0xPLMnMz0vMAfGjzOLNDH0MPAzcDbz8vTxNDRy9_Y2NQ13CDA3cDYEKIoEKnN0dPUzMfQwMDEwsjAw8XZw8XMwtfQ0MPM2I02-AAzgaENIfrh-FqsQ9wBmoxN_FydLAGAgNTKEK8DkRrACPGwpyQyMMMj0VAbNnwlU!/dl5/d5/L2dBISEvZ0FBIS9nQSEh/pw/Z7_HGK818G0KOCO10AFFGUTGU0004/res/id=buscaResultado/c=cacheLevelPage/=/?timestampAjax=1518194221050&concurso={}'


def ts_now():
    """Unix timestamp in seconds
    """
    from datetime import datetime

    time = datetime.now()
    ts = time.timestamp()
    return int(ts)


def get_loteca_last_round():
    """Retrieves the last round number
    """
    url = FIRST_URL.format(ts_now() * 1000)
    session = requests_retry_session(total=5, backoff_factor=0.1)
    response = session.get(url)

    roundno = response.json()['concurso']
    return roundno


def retrieve_rounds(roundnos):
    """Retrieve loteca rounds
    """
    rounds = []

    for roundno in roundnos:
        click.echo("Retrieving round #{}".format(roundno))
        session = requests_retry_session(total=5, backoff_factor=0.3)
        response = session.get(QUERY_URL.format(roundno))
        round = response.json()
        rounds.append(round)

    return rounds


def collect_and_save_rounds(filepath):
    """Collect unscraped loteca rounds and save them
    """
    # get rounds already collected
    try:
        already_scraped = load_pickle(filepath)
    except FileNotFoundError:
        already_scraped = []

    # determine rounds not yet present
    last_round = get_loteca_last_round()
    already_scraped_nos = [r['concurso'] for r in already_scraped]
    rounds_to_scrap = sorted(
            set(range(1, last_round + 1)) - set(already_scraped_nos))

    click.echo("There are {} rounds to collect".format(len(rounds_to_scrap)))

    # scrap and save
    new_rounds = retrieve_rounds(rounds_to_scrap)
    all_rounds = already_scraped + new_rounds
    save_pickle(filepath, all_rounds)


@click.command()
@click.argument('io-loteca-site', type=click.Path(writable=True))
def CLI(io_loteca_site):
    """Collect rounds data from the loteca site

    In between the rounds data, there is the matches data, which is the focus
    of this script.

    This script can be used both for the first extraction or updates.

    \b
    Inputs:
        loteca-site (pkl): A list of dictionaries corresponding to rounds
            already scraped.

    \b
    Outputs:
        loteca-site (pkl): Same as the input. The new rounds will be saved
            here.
    """
    collect_and_save_rounds(io_loteca_site)


if __name__ == '__main__':
    CLI()
