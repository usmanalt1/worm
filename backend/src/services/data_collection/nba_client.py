import logging
import time as t

import pandas as pd

from services.data_collection.nba_proxy import configure_proxy
from services.data_collection.transformer_helper import TransformHelper

logger = logging.getLogger(__name__)

configure_proxy()

DEFAULT_HEADERS = {
    "Accept": "application/json, text/plain, /",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Host": "stats.nba.com",
    "Origin": "https://www.nba.com",
    "Pragma": "no-cache",
    "Referer": "https://www.nba.com/",
    "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
}

MAX_RETRIES = 5
BACKOFF_BASE = 2
RATE_LIMIT_SECONDS = 1
TIMEOUT_SECONDS = 60


class NBACollectionError(RuntimeError):
    pass


def _first_frame(response) -> pd.DataFrame:
    return response.get_data_frames()[0]


class NBAClient:
    """Every stats.nba.com call: headers, timeout, retry with backoff, rate limiting."""

    def __init__(self, max_retries: int = MAX_RETRIES, rate_limit_seconds: float = RATE_LIMIT_SECONDS):
        self.max_retries = max_retries
        self.rate_limit_seconds = rate_limit_seconds
        self.headers = DEFAULT_HEADERS
        self._transform = TransformHelper()

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._transform.clean_dataframe(df)

    def to_date(self, value) -> str:
        return self._transform.convert_date_format(value)

    def fetch(self, endpoint, *args, extract=_first_frame, **params) -> pd.DataFrame:
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = endpoint(*args, headers=self.headers, timeout=TIMEOUT_SECONDS, **params)
                df = self.clean(extract(response))
                t.sleep(self.rate_limit_seconds)
                return df
            except Exception as error:
                last_error = error
                logger.warning(
                    f"{endpoint.__name__} attempt {attempt}/{self.max_retries} failed: {error}"
                )
                if attempt < self.max_retries:
                    t.sleep(BACKOFF_BASE ** attempt)

        raise NBACollectionError(
            f"{endpoint.__name__} failed after {self.max_retries} attempts"
        ) from last_error

    def fetch_each(self, endpoint, entity_ids: list, id_column: str = None, **params) -> pd.DataFrame:
        """Fan one endpoint over entity ids, skipping any that keep failing.

        A partial roster beats no roster, so one dead team id does not fail the run.
        """
        frames = []
        for entity_id in entity_ids:
            try:
                df = self.fetch(endpoint, entity_id, **params)
            except NBACollectionError:
                logger.exception(f"Giving up on {endpoint.__name__} for id {entity_id}")
                continue
            if id_column:
                df[id_column] = entity_id
            frames.append(df)

        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)
