import logging

import pandas as pd

from services.data_collection.collectors.base import Collector
from services.data_collection.constants import Constants
from services.data_collection.request import Grain, WorkItem
from services.injuries.service import InjuryFeedService

logger = logging.getLogger(__name__)


class PlayerInjuries(Collector):
    """Today's injury snapshot, keyed by the date it was taken."""

    name = "player_injuries"
    table = Constants.PLAYER_INJURIES
    grain = Grain.SNAPSHOT
    backfillable = False

    def fetch(self, item: WorkItem, deps: dict) -> pd.DataFrame:
        # Third-party and additive, so a failure returns nothing rather than raising: the
        # night's predictions must not depend on an outside feed being up.
        try:
            df = InjuryFeedService().fetch_nba()
        except Exception:
            logger.exception("Injury feed unavailable; continuing without today's snapshot")
            return pd.DataFrame()

        if df is None or df.empty:
            logger.warning("Injury feed returned no rows")
            return pd.DataFrame()

        df["collected_date"] = item.as_of
        return df
