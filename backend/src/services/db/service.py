
import math
from typing import TypeVar, Optional
from django.db.models import Model
from app.models import (
    FctPlayerStats, FctTeamStats,
    FctAdvancedPlayerSeasonStats, FctAdvancedTeamSeasonStats,
    DimPlayers, DimRosters, DimSeasons, DimGames, DimTeams,
)
from django.db.models import Avg, Count, ExpressionWrapper, F, FloatField, Max, Q, Sum, Value
from django.db.models.functions import NullIf, Round

ROUND = 1
M = TypeVar("M", bound=Model)


def _no_nan(value):
    """JSON has no NaN literal, and Postgres stores NaN for a rate with no attempts."""
    return None if isinstance(value, float) and math.isnan(value) else value


def _shooting_pct(made: str, attempted: str):
    """Shooting percentage from season totals: averaging per-game ratios overweights
    a 1-for-1 night."""
    return Round(
        ExpressionWrapper(
            Sum(made) * Value(100.0) / NullIf(Sum(attempted), Value(0.0)),
            output_field=FloatField(),
        ),
        ROUND,
    )


def _box_score_averages() -> dict:
    """Per-game averages for every stat on the box-score fact tables."""
    return dict(
        average_minutes=Round(Avg("min"), ROUND),
        average_points=Round(Avg("pts"), ROUND),
        average_field_goals_made=Round(Avg("fgm"), ROUND),
        average_field_goals_attempted=Round(Avg("fga"), ROUND),
        average_three_pointers_made=Round(Avg("fg3m"), ROUND),
        average_three_pointers_attempted=Round(Avg("fg3a"), ROUND),
        average_free_throws_made=Round(Avg("ftm"), ROUND),
        average_free_throws_attempted=Round(Avg("fta"), ROUND),
        average_offensive_rebounds=Round(Avg("oreb"), ROUND),
        average_defensive_rebounds=Round(Avg("dreb"), ROUND),
        average_rebounds=Round(Avg("reb"), ROUND),
        average_assists=Round(Avg("ast"), ROUND),
        average_steals=Round(Avg("stl"), ROUND),
        average_blocks=Round(Avg("blk"), ROUND),
        average_turnovers=Round(Avg("tov"), ROUND),
        average_fouls=Round(Avg("pf"), ROUND),
        average_plus_minus=Round(Avg("plus_minus"), ROUND),
        field_goal_pct=_shooting_pct("fgm", "fga"),
        three_point_pct=_shooting_pct("fg3m", "fg3a"),
        free_throw_pct=_shooting_pct("ftm", "fta"),
    )

class Service:
    def __init__(self, model: M):
        self.model: M = model
    
    def get_all_players(self, season_name = None, team_id = None) -> list:
        if team_id and season_name:
            player_ids = DimRosters.objects.filter(season=str(season_name)).filter(team_id=str(team_id)).values_list("player_id", flat=True)
            return list(self.model.objects.filter(player_id__in=player_ids).only("player_id", "player_name"))

        if team_id:
            player_ids = DimRosters.objects.filter(team_id=str(team_id)).values_list("player_id", flat=True)
            return list(self.model.objects.filter(player_id__in=player_ids).only("player_id", "player_name"))

        if season_name:
            player_ids = DimRosters.objects.filter(season=str(season_name)).values_list("player_id", flat=True)
            return list(self.model.objects.filter(player_id__in=player_ids).only("player_id", "player_name"))
        
        return list(self.model.objects.only("player_id", "player_name"))
    
    def get_seasons_with_stats(self, season_type: str = "regular") -> list:
        """Seasons with recorded games of this type, newest last."""
        played = set(
            FctPlayerStats.objects.filter(season_type=season_type)
            .values_list("season", flat=True)
            .distinct()
        )
        seasons = [s for s in DimSeasons.objects.all() if s.season_name in played]
        return sorted(seasons, key=lambda s: s.season_name or "")

    def get_all_seasons(self) -> list:
        return list(self.model.objects.only("season_id", "season_name"))
    
    def get_all_teams(self) -> list:
        """One entry per team, for pickers."""
        latest_by_team = {}
        for team in self.model.objects.only("team_id", "team_name", "season").order_by("season"):
            latest_by_team[team.team_id] = team
        return sorted(latest_by_team.values(), key=lambda t: t.team_name or "")
    
    def get_team_colours(self) -> list:
        """One row per team, newest season winning, so a rebrand shows current."""
        latest_by_team = {}
        for row in self.model.objects.values(
            "team_id", "team_name", "display_hex", "alt_display_hex", "season",
            abbreviation=F("team_abbreviation"),
        ).order_by("season"):
            latest_by_team[row["team_id"]] = row
        return sorted(latest_by_team.values(), key=lambda r: r["abbreviation"] or "")

    def get_latest_games(self, season: str, season_type: str) -> list:
        dim_games_model: DimGames = self.model
        # This model holds the whole season, and a game with no result yet has null
        # scores - including games tipping off tonight alongside ones already final.
        played = dim_games_model.objects.filter(
            season=season,
            season_type=season_type,
            home_pts__isnull=False,
            away_pts__isnull=False,
        )
        latest_date = (
            played
            .order_by("-game_date")
            .values_list("game_date", flat=True)
            .distinct()[:5]
        )
        if not latest_date:
            return []

        return list(
            played.filter(game_date__in=latest_date)
            .only("game_id", "game_date", "season", "home_team_name", "away_team_name", "home_pts", "away_pts")
        )

    def get_game_box_score(self, game_id: str) -> dict:
        """Every player line from one game, plus the game header."""
        game = DimGames.objects.filter(game_id=game_id).first()
        if game is None:
            return {}

        lines = list(
            FctPlayerStats.objects.filter(game_id=game_id)
            .values(
                "player_id", "player_name", "team_id", "min", "pts", "reb", "oreb", "dreb",
                "ast", "stl", "blk", "tov", "pf", "fgm", "fga", "fg_pct", "fg3m", "fg3a",
                "fg3_pct", "ftm", "fta", "ft_pct", "plus_minus",
            )
            .order_by("-pts")
        )
        return {"game": game, "lines": [{k: _no_nan(v) for k, v in line.items()} for line in lines]}

    def get_all_player_stats(self, season_id: Optional[int] = None) -> list:
        queryset = FctPlayerStats.objects.select_related("player").values("player_id", "season_id", "pts", "reb", "plus_minus", "ast", "player__player_name")
        if season_id is not None:
            queryset = queryset.filter(season_id=str(season_id))
        return list(queryset)
    
    def get_season_player_stats(
        self,
        season_name: str,
        team_id: Optional[int] = None,
        position: Optional[str] = None,
        season_type: str = "regular",
    ) -> list:
        """Per-game averages for every player in a season, one row per player."""
        # Never traverse the player FK: dim_players covers the latest season only, so the
        # inner join drops every earlier player.
        qs = FctPlayerStats.objects.filter(
            season=str(season_name), season_type=season_type,
        )
        if team_id:
            qs = qs.filter(team_id=team_id)
        if position:
            # Resolved to ids first, so this stays a filter rather than a join.
            matching_ids = DimPlayers.objects.filter(
                position__icontains=position,
            ).values_list("player_id", flat=True)
            qs = qs.filter(player_id__in=list(matching_ids))

        rows = list(
            qs.values("player_id", "season")
            .annotate(
                games_played=Count("game_id", distinct=True),
                # Max, not a group-by: the source spells some names two ways.
                player_name=Max("player_name"),
                **_box_score_averages(),
            )
            .order_by("-average_points")
        )
        positions = dict(DimPlayers.objects.values_list("player_id", "position"))
        for row in rows:
            row["position"] = positions.get(row["player_id"])
        return rows

    def get_season_team_stats(
        self,
        season_name: str,
        team_id: Optional[int] = None,
        season_type: str = "regular",
    ) -> list:
        """Per-game averages and win/loss record for each team in a season."""
        qs = FctTeamStats.objects.filter(season=str(season_name), season_type=season_type)
        if team_id:
            qs = qs.filter(team_id=team_id)

        rows = list(
            qs.values("team_id", "season")
            .annotate(
                games_played=Count("game_id", distinct=True),
                wins=Count("game_id", filter=Q(wl="W"), distinct=True),
                losses=Count("game_id", filter=Q(wl="L"), distinct=True),
                **_box_score_averages(),
            )
            .order_by("-wins")
        )
        # fct_team_stats has no FK to dim_teams, so attach names from one lookup.
        names = dict(DimTeams.objects.values_list("team_id", "team_name"))
        for row in rows:
            row["team_name"] = names.get(row["team_id"], str(row["team_id"]))
        return rows

    def get_season_advanced_player_stats(
        self,
        season_name: str,
        team_id: Optional[int] = None,
        position: Optional[str] = None,
        season_type: str = "regular",
    ) -> list:
        """Advanced season stats per player; the source is already one row per season."""
        qs = FctAdvancedPlayerSeasonStats.objects.filter(
            season=str(season_name), season_type=season_type,
        )
        if team_id:
            qs = qs.filter(team_id=team_id)
        if position:
            # Ids first, as above: joining dim_players would drop earlier players.
            matching_ids = DimPlayers.objects.filter(
                position__icontains=position,
            ).values_list("player_id", flat=True)
            qs = qs.filter(player_id__in=list(matching_ids))

        rows = list(qs.values().order_by("-pie"))
        positions = dict(DimPlayers.objects.values_list("player_id", "position"))
        for row in rows:
            row["position"] = positions.get(row["player_id"])
        return rows

    def get_season_advanced_team_stats(
        self,
        season_name: str,
        team_id: Optional[int] = None,
        season_type: str = "regular",
    ) -> list:
        """Advanced season stats per team - a straight read, no aggregation."""
        qs = FctAdvancedTeamSeasonStats.objects.filter(
            season=str(season_name), season_type=season_type,
        )
        if team_id:
            qs = qs.filter(team_id=team_id)
        return list(qs.values().order_by("-net_rating"))

    def get_player_stats(
        self,
        player_id: Optional[str] = None,
        season_id: Optional[int] = None,
        season_type: str = "regular",
    ) -> list:
        """Per-game averages grouped by season; season_type None combines both."""
        qs = FctPlayerStats.objects.select_related("player")
        if season_type:
            qs = qs.filter(season_type=season_type)
        if player_id:
            qs = qs.filter(player_id=player_id)
        if season_id:
            qs = qs.filter(season=str(season_id))

        if player_id:
            group_fields = ["season_id"]
        else:
            group_fields = ["player_id", "season_id", "season", "player__player_name"]

        player_stats = qs.values(*group_fields).annotate(
            average_points=Round(Avg("pts"), ROUND),
            average_rebounds=Round(Avg("reb"), ROUND),
            average_plus_minus=Round(Avg("plus_minus"), ROUND),
            average_assists=Round(Avg("ast"), ROUND),
        )
        if player_id:
            player_stats = player_stats.annotate(player_id=Round(Max("player_id"), ROUND))
        
        player_stats = player_stats.annotate(player_name=Max("player__player_name"))
        return list(player_stats)
