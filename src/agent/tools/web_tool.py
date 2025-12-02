import requests
from typing import Tuple

def fetch_url(url: str, timeout: int = 10) -> Tuple[bool, str]:
    """Fetch a URL and return (success, text_or_error)."""
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return True, resp.text
    except Exception as e:
        return False, str(e)
