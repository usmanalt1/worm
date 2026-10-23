import pandas as pd
from nba_api.stats.endpoints import scheduleleaguev2

from services.data_collection.collectors.base import Collector
from services.data_collection.constants import Constants
from services.data_collection.request import Grain, WorkItem


class GameSchedule(Collector):
    """Full-season schedule; unlike the box-score sources, future games exist as rows."""

    name = "game_schedule"
    table = Constants.GAME_SCHEDULE
    grain = Grain.REFERENCE

    def fetch(self, item: WorkItem, deps: dict) -> pd.DataFrame:
        df = self.client.fetch(
            scheduleleaguev2.ScheduleLeagueV2,
            season=item.season_year,
            extract=lambda response: response.season_games.get_data_frame(),
        )
        df = df.rename(columns={
            "gameid": "game_id",
            "gamedateest": "game_date",
            "hometeam_teamid": "home_team_id",
            "awayteam_teamid": "away_team_id",
            "gamestatus": "game_status",
        })
        df = df[["game_id", "game_date", "home_team_id", "away_team_id", "game_status"]].copy()
        df["game_date"] = df["game_date"].apply(self.client.to_date)
        df["season_id"] = int(item.season_id)
        df["season"] = item.season_year
        return df
