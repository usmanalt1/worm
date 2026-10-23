import pandas as pd
from nba_api.stats.endpoints import leaguedashplayerstats, leaguedashteamstats

from app.models import AdvancedPlayerSeasonStats as AdvancedPlayerSeasonStatsModel
from app.models import AdvancedTeamSeasonStats as AdvancedTeamSeasonStatsModel
from services.data_collection.collectors.base import Collector
from services.data_collection.constants import Constants
from services.data_collection.request import STORED_SEASON_TYPE, Grain, WorkItem


class _AdvancedSeasonStats(Collector):
    grain = Grain.PER_SEASON_ENTITY
    by_season_type = True
    endpoint = None

    def fetch(self, item: WorkItem, deps: dict) -> pd.DataFrame:
        df = self.client.fetch(
            self.endpoint,
            season=item.season_year,
            season_type_all_star=item.season_type,
            measure_type_detailed_defense="Advanced",
            per_mode_detailed="PerGame",
        )
        # The *_RANK and sp_work_* columns are derivable from the rest.
        df = df[[c for c in df.columns if not c.endswith("_rank") and not c.startswith("sp_work")]]
        df["season_id"] = str(item.season_id)
        df["season"] = item.season_year
        df["season_type"] = STORED_SEASON_TYPE[item.season_type]
        return df


class AdvancedPlayerSeasonStats(_AdvancedSeasonStats):
    name = "advanced_player_season"
    table = Constants.ADVANCED_PLAYER_SEASON_STATS
    endpoint = leaguedashplayerstats.LeagueDashPlayerStats
    model = AdvancedPlayerSeasonStatsModel
    dedupe_on = ("season", "season_type", "player_id")


class AdvancedTeamSeasonStats(_AdvancedSeasonStats):
    name = "advanced_team_season"
    table = Constants.ADVANCED_TEAM_SEASON_STATS
    endpoint = leaguedashteamstats.LeagueDashTeamStats
    model = AdvancedTeamSeasonStatsModel
    dedupe_on = ("season", "season_type", "team_id")
