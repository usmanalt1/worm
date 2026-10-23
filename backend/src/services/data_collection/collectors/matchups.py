import pandas as pd
from nba_api.stats.endpoints import leaguegamefinder

from services.data_collection.collectors.base import Collector
from services.data_collection.constants import Constants
from services.data_collection.request import PLAYOFFS, Grain, WorkItem


class TeamMatchups(Collector):
    name = "team_matchups"
    table = Constants.TEAM_MATCHUPS
    grain = Grain.PER_SEASON_ENTITY
    requires = ("team_info",)

    def fetch(self, item: WorkItem, deps: dict) -> pd.DataFrame:
        team_ids = pd.unique(deps["team_info"]["id"]).tolist()
        frames = []
        for team_id in team_ids:
            # Playoffs are a separate call: LeagueGameFinder defaults to regular season only.
            for season_type in (None, PLAYOFFS):
                params = {"team_id_nullable": team_id, "season_nullable": item.season_year}
                if season_type:
                    params["season_type_nullable"] = season_type
                frames.append(self.client.fetch(leaguegamefinder.LeagueGameFinder, **params))

        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True).dropna()
