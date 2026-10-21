from nba_api.stats.endpoints import scoreboardv2
from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonallplayers, commonteamroster
from nba_api.stats.endpoints import teamgamelog
import pandas as pd
from services.data_collection.transformer_helper import TransformHelper
import logging
from nba_api.stats.endpoints import leagueleaders, teamdashboardbygeneralsplits, leaguegamefinder, playbyplayv3, playerawards
from nba_api.stats.endpoints import leaguegamelog
from nba_api.stats.endpoints import leaguedashplayerstats, leaguedashteamstats
from nba_api.stats.endpoints import scheduleleaguev2
from nba_api.stats.endpoints import drafthistory
from http.client import RemoteDisconnected
from services.data_collection.constants import Constants
from nba_api.stats.library.parameters import SeasonTypePlayoffs, SeasonType, SeasonTypeAllStar
import nba_api.library.http as nba_http
import os
import time as t

# stats.nba.com blackholes datacenter IPs, so a scheduled run off a cloud runner needs
# to egress through a residential proxy. Set here rather than threaded through every
# endpoint call: http.py falls back to this global whenever a call passes proxy=None,
# which all of them do.
_NBA_PROXY = os.getenv("NBA_PROXY")
if _NBA_PROXY:
    if not hasattr(nba_http, "PROXY"):
        raise RuntimeError(
            "nba_api.library.http.PROXY is gone, so NBA_PROXY would be ignored and every "
            "request would egress unproxied. Pin nba_api or pass proxy= per call instead."
        )
    nba_http.PROXY = _NBA_PROXY
    logging.getLogger(__name__).info("Routing stats.nba.com requests through NBA_PROXY")

SHOOTING_PCT_COLS = ["fg_pct", "fg3_pct", "ft_pct"]

class CollectRawNBAData(TransformHelper, Constants):

    def __init__(self, **kwargs):
        self.date = kwargs["date_to_run"]
        self.season_id = self.create_season_id_year().get("season_id")
        self.season_year = self.create_season_id_year().get("season_year")
        self.headers = {
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

    def gather_and_import_nba_data(self, table_name = None, season_id: str = None, season_year: str = None, team_roster = None, game_schedule: bool = False) -> dict:
        if season_id is None:
            season_id = self.season_id
        if season_year is None:
            season_year = self.season_year

        if table_name:
            logging.info(f"Gathering data for table: {table_name}")
            if table_name == "team_stats" or table_name == "team_roster":
                df = getattr(self, f"_get_{table_name}")(df_team_roster=self._get_team_info(), season_year=season_year, season_id=season_id)
            elif table_name == "player_stats":
                df = getattr(self, f"_get_{table_name}")(season_year=season_year, season_id=season_id)
            else:
                df = getattr(self, f"_get_{table_name}")()
            upper_case_table_name = table_name.upper()
            nba_data_dict = {
                getattr(self, upper_case_table_name): df,
            }
        else:
            logging.info("Gathering data for all tables")
            logging.info(f"Season_ID: {season_id}")
            logging.info(f"Season_Year: {season_year}")
            if game_schedule:
                logging.info("Collecting Game Schedule...")
                df_game_schedule = self._get_game_schedule(season_year=season_year, season_id=season_id)
                nba_data_dict = {self.GAME_SCHEDULE: df_game_schedule}

                return nba_data_dict

            df_season = self._get_season_record(season_id=season_id)
            df_teams = self._get_team_info()
            df_players = self._get_players_info(season_year=season_year)
            # Without preseason, those games sit in dim_games with no result forever.
            log_season_types = [
                SeasonType.default,
                SeasonTypePlayoffs.playoffs,
                SeasonTypeAllStar.preseason,
            ]

            team_log_frames = [
                self._get_logs(season_year=season_year, pt_abbreviation="T", season_type=st)
                for st in log_season_types
            ]
            df_team_logs = pd.concat(team_log_frames, ignore_index=True)
            df_team_logs = df_team_logs.drop_duplicates(subset=["game_id", "team_id"], keep="last")
            df_team_logs = df_team_logs.dropna()

            player_log_frames = [
                self._get_logs(season_year=season_year, pt_abbreviation="P", season_type=st)
                for st in log_season_types
            ]
            df_player_logs = pd.concat(player_log_frames, ignore_index=True)
            df_player_logs = df_player_logs.drop_duplicates(subset=["game_id", "player_id"], keep="last")
            df_player_logs[SHOOTING_PCT_COLS] = df_player_logs[SHOOTING_PCT_COLS].fillna(0)
            df_player_logs = df_player_logs.dropna(subset=["game_id", "player_id", "team_id"])
            df_team_matchups = self._get_team_matchups(team_roster=df_teams, season_year=season_year)

            nba_data_dict = {
                self.SEASON_RECORD: df_season,
                self.TEAMS_INFO: df_teams,
                self.PLAYERS_INFO: df_players,
                self.TEAM_STATS: df_team_logs,
                self.PLAYER_STATS: df_player_logs,
                self.TEAM_MATCHUPS: df_team_matchups,
            }
            if team_roster:
                nba_data_dict[self.TEAMS_ROSTER] = self._get_team_roster(df_team_info=df_teams, season_year=season_year, season_id=season_id)
        return nba_data_dict

    def _get_advanced_season_stats(self, season_year: str, season_id: str, season_type: str) -> dict:
        """Season-level advanced stats for every player and team, in two API calls.

        season_type is the nba_api value ("Regular Season" or "Playoffs").
        """
        logging.info(f"Collecting advanced season stats for {season_year} ({season_type})")
        frames = {}
        for table_name, endpoint in (
            (self.ADVANCED_PLAYER_SEASON_STATS, leaguedashplayerstats.LeagueDashPlayerStats),
            (self.ADVANCED_TEAM_SEASON_STATS, leaguedashteamstats.LeagueDashTeamStats),
        ):
            df = None
            max_retries = 5
            backoff_base = 2
            for attempt in range(1, max_retries + 1):
                try:
                    response = endpoint(
                        season=season_year,
                        season_type_all_star=season_type,
                        measure_type_detailed_defense="Advanced",
                        per_mode_detailed="PerGame",
                        headers=self.headers,
                        timeout=60,
                    )
                    df = self.clean_dataframe(response.get_data_frames()[0])
                    break
                except (RemoteDisconnected, Exception) as e:
                    logging.warning(
                        f"Error fetching {table_name} for {season_year} "
                        f"on attempt {attempt}/{max_retries}: {e}"
                    )
                    if attempt < max_retries:
                        t.sleep(backoff_base ** attempt)

            if df is None or df.empty:
                logging.error(f"No {table_name} returned for {season_year} ({season_type})")
                frames[table_name] = pd.DataFrame()
                continue

            # The *_RANK and sp_work_* columns are derivable from the rest.
            df = df[[c for c in df.columns if not c.endswith("_rank") and not c.startswith("sp_work")]]
            df["season_id"] = str(season_id)
            df["season"] = season_year
            df["season_type"] = "playoffs" if season_type == SeasonTypePlayoffs.playoffs else "regular"
            frames[table_name] = df
            t.sleep(1)  # to avoid rate limiting

        logging.info("...Raw Advanced Season Stats DFs Generated")
        return frames

    def _get_season_record(self, season_id: str) -> pd.DataFrame:

        season_year_dict = {"season_id": [int(season_id)]}
        df_from_dict = pd.DataFrame.from_dict(season_year_dict)

        logging.info("...Raw Season Info DF Generated")
        return df_from_dict

    def _get_games_played(self) -> pd.DataFrame:
        games = scoreboardv2.ScoreboardV2(day_offset=1, game_date=self.today)
        df_team_games_ids = games.get_data_frames()[0]

        return df_team_games_ids

    def _get_team_info(self) -> pd.DataFrame:
        df_team_info = pd.DataFrame(teams.get_teams())
        df_team_info = self.clean_dataframe(df_team_info)
        df_team_info["season_id"] = int(self.season_id)

        logging.info("...Raw Team Info DF Generated")
        return df_team_info

    def _get_team_roster(self, df_team_info: pd.DataFrame, season_year: str, season_id) -> pd.DataFrame:
        """Team rosters for the season, the source of the player ids the stat calls need."""
        logging.info("Collecting team rosters for each team in the season")
        team_ids = df_team_info["id"].values.tolist()
        all_teams = self.transfrom_data(
            commonteamroster.CommonTeamRoster, team_ids, season=season_year, headers=self.headers
        )
        all_teams = self.clean_dataframe(all_teams)
        all_teams["team_id"] = all_teams["teamid"]
        df_team_rosters = all_teams[
            ["team_id", "player_id", "player", "age", "position"]
        ]
        df_team_rosters["season_id"] = int(season_id)

        logging.info("...Raw Team Roster DF Generated")
        return df_team_rosters

    def _get_team_logs(self, df_team_roster: pd.DataFrame, season_year: str, season_id: str) -> pd.DataFrame:
        team_ids = df_team_roster["team_id"].values.tolist()
        df_all_team_logs = self.transfrom_data(
            teamgamelog.TeamGameLog, team_ids, season=season_year
        )
        df_all_team_logs = self.clean_dataframe(df_all_team_logs)
        df_all_team_logs["teamid"] = df_all_team_logs["team_id"]
        df_all_team_logs["game_date"] = df_all_team_logs["game_date"].apply(
            self.convert_date_format
        )
        df_all_team_logs["season_id"] = int(season_id)
        df_all_team_logs

        logging.info("...Raw Team Game Logs DF Generated")
        return df_all_team_logs

    def _get_players_info(self, season_year: str) -> pd.DataFrame:
        """Every player the league lists for the season, from the live endpoint."""
        raw = self.clean_dataframe(
            commonallplayers.CommonAllPlayers(
                season=season_year,
                is_only_current_season=1,
                headers=self.headers,
                timeout=60,
            ).get_data_frames()[0]
        )
        # "Last, First" splits on the comma; a full name split on spaces would put a
        # suffix like "Jr." in the wrong field.
        names = raw["display_last_comma_first"].astype(str).str.split(", ", n=1, expand=True)
        df_players = pd.DataFrame({
            "id": raw["person_id"],
            "full_name": raw["display_first_last"],
            "first_name": names[1].fillna(""),
            "last_name": names[0].fillna(""),
            "is_active": raw["rosterstatus"] == 1,
            "season_id": int(self.season_id),
        })

        logging.info("...Raw Player Info DF Generated")
        return df_players

    def _get_player_stats(self, season_year: str, season_id: str):
        leaders = leagueleaders.LeagueLeaders(season=season_year)
        df = leaders.get_data_frames()[0]
        df = self.clean_dataframe(df)
        df["season_id"] = int(season_id)
        df["date"] = self.date.strftime("%Y-%m-%d")
        df = df.dropna()
        logging.info("...Raw Player Averages DF Generated")
        return df


    def _get_logs(self, season_year: str, pt_abbreviation: str, season_type: str = SeasonType.default) -> pd.DataFrame:
        logging.info(f"Collecting logs for season: {season_year} and type: {pt_abbreviation}")
        max_retries = 5
        backoff_base = 2
        df_league_logs = None
        for attempt in range(1, max_retries + 1):
            try:
                league_logs = leaguegamelog.LeagueGameLog(
                    season=season_year,
                    player_or_team_abbreviation=pt_abbreviation,
                    headers=self.headers,
                    season_type_all_star=season_type,
                    timeout=60,
                )
                df_league_logs = league_logs.get_data_frames()[0]
                break
            except RemoteDisconnected as e:
                logging.warning(
                    f"RemoteDisconnected on attempt {attempt}/{max_retries}: {e}. Retrying..."
                )
            except Exception as e:
                logging.warning(
                    f"Error fetching league game logs on attempt {attempt}/{max_retries}: {e}. Retrying..."
                )

            if attempt < max_retries:
                t.sleep(backoff_base ** attempt)
            else:
                logging.error(
                    f"Failed to fetch league game logs after {max_retries} attempts"
                )
                raise
        df_league_logs = self.clean_dataframe(df_league_logs)
        df_league_logs["game_date"] = df_league_logs["game_date"].apply(
            self.convert_date_format
        )
        logging.info("...Raw League Game Logs DF Generated")
        return df_league_logs
    
    def _get_team_stats(self, df_team_roster, season_year: str, season_id: str) -> pd.DataFrame:
        team_ids = df_team_roster["id"].values.tolist()
        df_all_team_logs = self.transfrom_data(
            teamdashboardbygeneralsplits.TeamDashboardByGeneralSplits,
            team_ids,
            season=season_year,
        )
        df_all_team_logs = self.clean_dataframe(df_all_team_logs)
        df_all_team_logs["season_id"] = int(season_id)
        df_all_team_logs["date"] = self.date.strftime("%Y-%m-%d")
        logging.info("...Raw Team Stats DF Generated")
        df_all_team_logs = df_all_team_logs.dropna()
        df_all_team_logs.drop(columns=["group_set", "group_value"], inplace=True)
        logging.info("...Raw Team Season Averages DF Generated")
        return df_all_team_logs

    def _get_team_matchups(self, team_roster: pd.DataFrame, season_year: str) -> pd.DataFrame:
        team_roster_ids = pd.unique(team_roster["id"]).tolist()
        logging.info("Count of Team IDs: {}".format(len(team_roster_ids)))
        all_games = pd.DataFrame()
        logging.info(f"Team IDs for Matchups: {team_roster_ids}")

        for team_id in team_roster_ids:
            game_finder_season = leaguegamefinder.LeagueGameFinder(team_id_nullable=team_id, season_nullable=season_year)
            game_finder_playoffs = leaguegamefinder.LeagueGameFinder(team_id_nullable=team_id, season_nullable=season_year, season_type_nullable=SeasonTypePlayoffs.playoffs)
            games = pd.concat([game_finder_season.get_data_frames()[0], game_finder_playoffs.get_data_frames()[0]], ignore_index=True)
            games = self.clean_dataframe(games)
            all_games = pd.concat([all_games, games], ignore_index=True)
            t.sleep(1)  # to avoid rate limiting
        logging.info("...Raw Team Matchups DF Generated")
        all_games = all_games.dropna()
        return all_games
    
    def _get_game_schedule(self, season_year: str = None, season_id: str = None) -> pd.DataFrame:
        """Full-season schedule; unlike the box-score sources, future games exist as rows."""
        season_year = season_year or self.season_year
        season_id = season_id or self.season_id

        schedule = scheduleleaguev2.ScheduleLeagueV2(season=season_year, headers=self.headers)
        df = schedule.season_games.get_data_frame()
        df = self.clean_dataframe(df)
        df = df.rename(columns={
            "gameid": "game_id",
            "gamedateest": "game_date",
            "hometeam_teamid": "home_team_id",
            "awayteam_teamid": "away_team_id",
            "gamestatus": "game_status",
        })
        df = df[["game_id", "game_date", "home_team_id", "away_team_id", "game_status"]].copy()
        df["game_date"] = df["game_date"].apply(self.convert_date_format)
        df["season_id"] = int(season_id)
        df["season"] = season_year

        logging.info("...Raw Game Schedule DF Generated")
        return df

    def _get_draft_history(self, draft_year: int) -> pd.DataFrame:
        """Every pick of one draft. A pick is never revised, so this is reference data."""
        logging.info(f"Collecting draft history for {draft_year}")

        response = drafthistory.DraftHistory(
            season_year_nullable=str(draft_year), headers=self.headers, timeout=60,
        )
        df = self.clean_dataframe(response.get_data_frames()[0])
        if df.empty:
            return df

        df = df.rename(columns={"person_id": "player_id", "season": "draft_year"})
        df = df[[
            "player_id", "player_name", "draft_year", "round_number", "round_pick",
            "overall_pick", "draft_type", "team_id",
        ]].copy()
        df["draft_year"] = df["draft_year"].astype(int)
        # The season the draft feeds, so this keys like every other table here.
        df["season"] = df["draft_year"].apply(lambda year: f"{year}-{str(year + 1)[2:]}")

        logging.info("...Raw Draft History DF Generated")
        return df

    def _get_player_awards(self, df_players: pd.DataFrame) -> pd.DataFrame:
        logging.info("Starting getting player awards...")
        # df_players is who to fetch awards for, not the award response (which keys on person_id)
        player_ids = pd.unique(df_players["player_id"]).tolist()

        all_player_awards = pd.DataFrame()
        length = len(player_ids)
        for p_id in player_ids:
            logging.info(f"Total players: {length}")
            length -= 1
            logging.info(f"Player left: {length}")
            player_awards = playerawards.PlayerAwards(player_id=p_id, headers=self.headers)
            player_awards = player_awards.get_data_frames()[0]
            player_awards = self.clean_dataframe(player_awards)
            player_awards.rename(columns={"person_id": "player_id"}, inplace=True)
            all_player_awards = pd.concat([all_player_awards, player_awards])
            t.sleep(1)

        logging.info("...Raw Player Awards Generated")
        # Subset dropna: most other columns are legitimately empty for some award types.
        if not all_player_awards.empty:
            all_player_awards = all_player_awards.dropna(subset=["player_id", "season", "description"])

        return all_player_awards


    def _play_by_play(self) -> pd.DataFrame:
        playbyplayv3.PlayByPlayV3(game_id="0022200001").get_data_frames()[0]