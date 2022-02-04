"""
uses https://github.com/seanbreckenridge/url_cache to cache
discogs API data locally
"""

import os
import functools
from functools import cache
from typing import Any, Dict, Tuple
from datetime import datetime
from urllib.parse import urlparse

import requests
import backoff  # type: ignore[import]
import discogs_client  # type: ignore[import]
from url_cache.core import (
    URLCache,
    Summary,
)

from . import SETTINGS
from .common import eprint


def backoff_hdlr(details):
    print(
        "Backing off {wait:0.1f} seconds afters {tries} tries "
        "calling function {target} with args {args} and kwargs "
        "{kwargs}".format(**details)
    )


@functools.lru_cache(1)
def discogsClient() -> discogs_client.Client:
    return discogs_client.Client(
        SETTINGS.DISCOGS_CREDS["user_agent"], user_token=SETTINGS.DISCOGS_CREDS["token"]
    )


@backoff.on_exception(
    lambda: backoff.constant(interval=10),
    (requests.exceptions.RequestException, discogs_client.exceptions.HTTPError),
    max_tries=5,
    on_backoff=backoff_hdlr,
)
def discogs_get(_type: str, _id: int, /) -> Dict[str, Any]:
    """Gets data from discogs API."""
    eprint(f"[Discogs] Requesting {_type} {_id}")
    if _type == "master":  # if Master
        resp = discogsClient().master(_id)
    elif _type == "release":
        resp = discogsClient().release(_id)
    else:
        raise RuntimeError(f"Unknown discogs request type: {_type}")
    resp.refresh()
    data = dict(resp.data)
    return data


def parse_url_type(uurl: str) -> Tuple[str, int]:
    _type, _id = urlparse(uurl).path.strip("/").split("/")
    assert _type in {"master", "release"}, str(uurl)
    assert str(_id).isdigit(), str(uurl)
    return _type, int(_id)


class DiscogsCache(URLCache):
    """
    Subclass URLCache to handle caching the Summary data to a local directory cache
    """

    def request_data(self, url: str) -> Summary:  # type: ignore[override]
        """
        Override the request data function to fetch from the discogs API
        """
        self.sleep()
        uurl = self.preprocess_url(url)
        assert uurl.strip(), f"No url: '{url}'"
        _type, _id = parse_url_type(uurl)
        data = discogs_get(_type, int(_id))
        assert len(data.keys()) > 3, str(data)
        # raises before it returns summary which would then get saved by 'URLCache.get'
        return Summary(url=uurl, data={}, metadata=data, timestamp=datetime.now())


@cache
def discogs_urlcache() -> DiscogsCache:
    default_local = os.path.join(os.environ["HOME"], ".local", "share")
    cache_dir = os.path.join(default_local, "discogs_urlcache")
    return DiscogsCache(cache_dir=cache_dir, sleep_time=1)


@cache
def fetch_discogs(url: str) -> Summary:
    uc = discogs_urlcache()
    data = uc.get(url)
    _type, _id = parse_url_type(url)
    # if this is the master release, request the main release for this as well
    if _type == "master":
        assert "main_release" in data.metadata, str(data)
        main_release_url = (
            f"https://discogs.com/release/{int(data.metadata['main_release'])}"
        )
        if not uc.summary_cache.has(main_release_url):
            eprint(f"[Discogs] Requesting main release for {_id}")
        uc.get(main_release_url)
    return data
