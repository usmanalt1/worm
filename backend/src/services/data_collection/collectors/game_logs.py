import pandas as pd
from nba_api.stats.endpoints import leaguegamelog

from services.data_collection.collectors.base import Collector
from services.data_collection.constants import Constants
from services.data_collection.request import Grain, WorkItem

SHOOTING_PCT_COLS = ["fg_pct", "fg3_pct", "ft_pct"]


class _GameLogs(Collector):
    grain = Grain.PER_GAME
    by_season_type = True
    player_or_team: str = None

    def _league_log(self, item: WorkItem) -> pd.DataFrame:
        df = self.client.fetch(
            leaguegamelog.LeagueGameLog,
            season=item.season_year,
            player_or_team_abbreviation=self.player_or_team,
            season_type_all_star=item.season_type,
        )
        df["game_date"] = df["game_date"].apply(self.client.to_date)
        return df


class TeamGameLogs(_GameLogs):
    name = "team_game_logs"
    table = Constants.TEAM_STATS
    player_or_team = "T"
    dedupe_on = ("game_id", "team_id")

    def fetch(self, item: WorkItem, deps: dict) -> pd.DataFrame:
        return self._league_log(item).dropna()


class PlayerGameLogs(_GameLogs):
    name = "player_game_logs"
    table = Constants.PLAYER_STATS
    player_or_team = "P"
    dedupe_on = ("game_id", "player_id")

    def fetch(self, item: WorkItem, deps: dict) -> pd.DataFrame:
        df = self._league_log(item)
        df[SHOOTING_PCT_COLS] = df[SHOOTING_PCT_COLS].fillna(0)
        return df.dropna(subset=["game_id", "player_id", "team_id"])
