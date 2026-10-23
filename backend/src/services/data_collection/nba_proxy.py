import logging
import os

import nba_api.library.http as nba_http

logger = logging.getLogger(__name__)


def configure_proxy() -> None:
    """Route stats.nba.com through NBA_PROXY if set; safe to call more than once.

    stats.nba.com blackholes datacenter IPs, so a scheduled run off a cloud runner needs
    to egress through a residential proxy. Set as a global rather than threaded through
    every endpoint call: http.py falls back to it whenever a call passes proxy=None,
    which all of them do.
    """
    proxy = os.getenv("NBA_PROXY")
    if not proxy:
        return

    if not hasattr(nba_http, "PROXY"):
        raise RuntimeError(
            "nba_api.library.http.PROXY is gone, so NBA_PROXY would be ignored and every "
            "request would egress unproxied. Pin nba_api or pass proxy= per call instead."
        )

    nba_http.PROXY = proxy
    logger.info("Routing stats.nba.com requests through NBA_PROXY")
