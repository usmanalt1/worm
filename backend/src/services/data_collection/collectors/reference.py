import pandas as pd
from nba_api.stats.endpoints import commonallplayers, commonteamroster
from nba_api.stats.static import teams

from services.data_collection.collectors.base import Collector
from services.data_collection.constants import Constants
from services.data_collection.request import Grain, WorkItem


class SeasonRecord(Collector):
    name = "season_record"
    table = Constants.SEASON_RECORD
    grain = Grain.REFERENCE

    def fetch(self, item: WorkItem, deps: dict) -> pd.DataFrame:
        return pd.DataFrame.from_dict({"season_id": [int(item.season_id)]})


class TeamInfo(Collector):
    name = "team_info"
    table = Constants.TEAMS_INFO
    grain = Grain.REFERENCE

    def fetch(self, item: WorkItem, deps: dict) -> pd.DataFrame:
        df = self.client.clean(pd.DataFrame(teams.get_teams()))
        df["season_id"] = int(item.season_id)
        return df


class PlayersInfo(Collector):
    name = "players_info"
    table = Constants.PLAYERS_INFO
    grain = Grain.PER_SEASON_ENTITY

    def fetch(self, item: WorkItem, deps: dict) -> pd.DataFrame:
        raw = self.client.fetch(
            commonallplayers.CommonAllPlayers,
            season=item.season_year,
            is_only_current_season=1,
        )
        # "Last, First" splits on the comma; a full name split on spaces would put a
        # suffix like "Jr." in the wrong field.
        names = raw["display_last_comma_first"].astype(str).str.split(", ", n=1, expand=True)
        return pd.DataFrame({
            "id": raw["person_id"],
            "full_name": raw["display_first_last"],
            "first_name": names[1].fillna(""),
            "last_name": names[0].fillna(""),
            "is_active": raw["rosterstatus"] == 1,
            "season_id": int(item.season_id),
        })


class TeamRoster(Collector):
    name = "team_roster"
    table = Constants.TEAMS_ROSTER
    grain = Grain.PER_SEASON_ENTITY
    requires = ("team_info",)

    def fetch(self, item: WorkItem, deps: dict) -> pd.DataFrame:
        team_ids = deps["team_info"]["id"].values.tolist()
        rosters = self.client.fetch_each(
            commonteamroster.CommonTeamRoster, team_ids, season=item.season_year,
        )
        if rosters.empty:
            return rosters

        rosters["team_id"] = rosters["teamid"]
        df_rosters = rosters[["team_id", "player_id", "player", "age", "position"]].copy()
        df_rosters["season_id"] = int(item.season_id)
        return df_rosters
