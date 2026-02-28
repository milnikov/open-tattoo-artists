"""HTTP client with retries, rate limiting, and jitter."""

import time
import random
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter


def create_session(
    retries=3,
    backoff_factor=3,
    status_forcelist=(429, 500, 502, 503, 504),
    jitter_min_ms=200,
    jitter_max_ms=600,
):
    """Create a requests Session with retry logic and rate limiting."""
    session = requests.Session()

    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["HEAD", "GET", "OPTIONS"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })

    def rate_limit():
        """Apply random delay between requests (200-600ms default)."""
        delay = random.uniform(jitter_min_ms / 1000.0, jitter_max_ms / 1000.0)
        time.sleep(delay)

    session.rate_limit = rate_limit
    return session


def get_with_retry(session, url, timeout=15, extra_delay_after=None):
    """
    GET with rate limiting before the request.
    If extra_delay_after is set, also sleeps that many seconds after (e.g. every N images).
    """
    session.rate_limit()
    try:
        resp = session.get(url, timeout=timeout)
        resp.raise_for_status()
        if extra_delay_after:
            time.sleep(extra_delay_after)
        return resp
    except requests.exceptions.HTTPError as e:
        if e.response.status_code in (429, 503):
            time.sleep(3)
        raise
