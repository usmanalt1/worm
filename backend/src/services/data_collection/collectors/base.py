from abc import ABC, abstractmethod

import pandas as pd

from services.data_collection.nba_client import NBAClient
from services.data_collection.request import Grain, WorkItem


class Collector(ABC):
    """One dataset. `table` is where it lands, `name` is what selects it."""

    name: str = None
    table: str = None
    grain: Grain = None
    # Does the pipeline fan this out over the requested season types?
    by_season_type: bool = False
    # False for a live snapshot with no history to re-collect; gathered once per run.
    backfillable: bool = True
    requires: tuple = ()
    dedupe_on: tuple = ()
    # Set where the endpoint returns columns the Django model deliberately does not store.
    model = None

    def __init__(self, client: NBAClient = None):
        self.client = client or NBAClient()

    @abstractmethod
    def fetch(self, item: WorkItem, deps: dict) -> pd.DataFrame:
        ...
