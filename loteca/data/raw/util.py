import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def requests_retry_session(**retry_kwargs):
    """This will create a requests session that can retry failed requests
    easily. 

    Gently copied from:
    https://www.peterbe.com/plog/best-practice-with-retries-with-requests
    
    For more information on the kwargs, look at:
    http://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html#module-urllib3.util.retry
    """
    session = requests.Session()
    retry = Retry(**retry_kwargs)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session
