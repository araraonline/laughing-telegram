import logging
import pickle
from datetime import datetime

import click
import click_log

from loteca.data.raw.util import requests_retry_session


FIRST_URL = r'http://loterias.caixa.gov.br/wps/portal/loterias/landing/loteca/!ut/p/a1/04_Sj9CPykssy0xPLMnMz0vMAfGjzOLNDH0MPAzcDbz8vTxNDRy9_Y2NQ13CDA3cDYEKIoEKnN0dPUzMfQwMDEwsjAw8XZw8XMwtfQ0MPM2I02-AAzgaENIfrh-FqsQ9wBmoxN_FydLAGAgNTKEK8DkRrACPGwpyQyMMMj0VAbNnwlU!/dl5/d5/L2dBISEvZ0FBIS9nQSEh/pw/Z7_HGK818G0KOCO10AFFGUTGU0004/res/id=buscaResultado/c=cacheLevelPage/=/?timestampAjax={}'
QUERY_URL = r'http://loterias.caixa.gov.br/wps/portal/!ut/p/a1/04_Sj9CPykssy0xPLMnMz0vMAfGjzOLNDH0MPAzcDbz8vTxNDRy9_Y2NQ13CDA3cDYEKIoEKnN0dPUzMfQwMDEwsjAw8XZw8XMwtfQ0MPM2I02-AAzgaENIfrh-FqsQ9wBmoxN_FydLAGAgNTKEK8DkRrACPGwpyQyMMMj0VAbNnwlU!/dl5/d5/L2dBISEvZ0FBIS9nQSEh/pw/Z7_HGK818G0KOCO10AFFGUTGU0004/res/id=buscaResultado/c=cacheLevelPage/=/?timestampAjax=1518194221050&concurso={}'

logger = logging.getLogger('loteca-site')
click_log.basic_config(logger)


def ts_now():
    """Unix timestamp in seconds"""
    time = datetime.now()
    ts = time.timestamp()
    return int(ts)

def get_last_round():
    """Retrieves the current Loteca round number"""
    url = FIRST_URL.format(ts_now() * 1000)

    session = requests_retry_session(total=5, backoff_factor=0.1)
    response = session.get(url)

    roundno = response.json()['concurso']
    return roundno

def get_scrapped_rounds(in_loteca_site):
    """Retrieves the rounds that have already been scrapped

    Args:
        in_loteca_site: the path to the file that was used to save the loteca
            rounds retrieved from the site

    Returns:
        A list of dictionaries, each one corresponding to a round that have
        already been scrapped. 
    """
    try:
        with open(in_loteca_site, mode='rb') as fp:
            rounds = pickle.load(fp)
    except FileNotFoundError:
        rounds = []

    return rounds
    
def retrieve_loteca_rounds(roundnos):
    """Collect raw loteca rounds

    Args:
        roundnos: a list of rounds numbers to be retrieved

    Returns:
        A list of dictionaries. Each dictionary corresponds to the json
        representation of the Loteca round.
    """
    rounds = []

    for roundno in roundnos:
        logger.info("Retrieving round #%s" % roundno)
        session = requests_retry_session(total=5, backoff_factor=0.3)
        response = session.get(QUERY_URL.format(roundno))
        round = response.json()
        rounds.append(round)

    return rounds

def _save_loteca_site(out_loteca_site):
    scrapped_rounds = get_scrapped_rounds(out_loteca_site)
    scrapped_nos = [r['concurso'] for r in scrapped_rounds]

    last_round = get_last_round()
    to_scrap = sorted(set(range(1, last_round + 1)) - set(scrapped_nos))

    logger.info("There are %s rounds to collect" % len(to_scrap))
    new_rounds = retrieve_loteca_rounds(to_scrap)

    rounds = scrapped_rounds + new_rounds
    with open(out_loteca_site, mode='wb') as fp:
        pickle.dump(rounds, fp)


# CLI

@click.command()
@click.argument('out-loteca-site', type=click.Path(writable=True))
@click_log.simple_verbosity_option(logger, default='INFO')
def save_loteca_site(out_loteca_site):
    """Collect rounds data from the loteca site

    This script can be used both to create a new file or to scrap from the
    beginning and create a new file.

    Outputs:
        out-loteca-site (pkl): the files where the raw rounds will be saved to.
        This is in the format of a list of dictionaries, each dictionary
        corresponding to a round.
    """
    _save_loteca_site(out_loteca_site)


if __name__ == '__main__':
    save_loteca_site()
