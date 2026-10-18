import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, log_loss, brier_score_loss, roc_auc_score
import pandas as pd

from services.ml_model.models.models_base import ModelBase
from services.ml_model.models.model_config import ModelsConfig
from services.ml_model.models.train_result import TrainResult
from services.ml_model.models.models_strategy import STRATEGY_REGISTRY
from services.db.db_service import DBService
from services.ml_model.features.boxscore_transformer import BoxscoreTransformer
from services.ml_model.features.playoff_boxscore_transformer import PlayoffBoxscoreTransformer
from services.ml_model.features.games_transformer import GamesTransformer
from services.ml_model.features.players_transfomer import PlayersTransformer
from services.ml_model.features.team_strength_transformer import TeamStrengthTransformer
from services.ml_model.features.schedule_load_transformer import ScheduleLoadTransformer
from services.ml_model.features.roster_value_transformer import RosterValueTransformer
from config.logger import get_logger

logger = get_logger(__name__)

MODE_BACKTEST = "backtest"
MODE_LIVE = "live"

SEASON_TYPE_PLAYOFFS = "playoffs"
SEASON_TYPE_REGULAR = "regular"
SEASON_TYPE_PRESEASON = "preseason"

# Preseason has no history to train on, so it is predicted off regular-season form.
TRAIN_SEASON_TYPE = {SEASON_TYPE_PRESEASON: SEASON_TYPE_REGULAR}


def _report(name, y_true, pred, proba) -> dict[str, float]:
    metrics = {
        "accuracy": accuracy_score(y_true, pred),
        "log_loss": log_loss(y_true, proba, labels=[0, 1]),
        "brier": brier_score_loss(y_true, proba),
        "auc": roc_auc_score(y_true, proba),
    }
    logger.info(
        f"{name:20s} acc={metrics['accuracy']:.3f}  logloss={metrics['log_loss']:.3f}  "
        f"brier={metrics['brier']:.3f}  auc={metrics['auc']:.3f}"
    )
    return metrics


class ModelTraner(ModelBase):
    def __init__(self, strategy: str, season: str, season_type: str, mode: str = MODE_BACKTEST):
        """Train `strategy` for `season`/`season_type`.

        backtest scores against all of a completed `season`; live trains on its played
        games and predicts the rest, so metrics come back empty.
        """
        if strategy not in STRATEGY_REGISTRY:
            raise ValueError(f"Unknown strategy: {strategy}")
        if mode not in (MODE_BACKTEST, MODE_LIVE):
            raise ValueError(f"Unknown mode: {mode}")

        logger.info(
            f"Initialising ModelTrainer with strategy={strategy}, season={season}, "
            f"season_type={season_type}, mode={mode}"
        )

        self.db_service = DBService()
        self.season = season
        self.season_type = season_type
        self.mode = mode
        (
            all_games, all_team_stats, all_player_stats,
            self.df_teams, self.df_team_strength, self.df_schedule_load,
            self.df_player_value, self.df_roster_history, self.df_current_roster,
        ) = self.load_data()

        self.train_season_type = TRAIN_SEASON_TYPE.get(season_type, season_type)
        self._select_frames(all_games, all_team_stats, all_player_stats)
        self.predicted_game_ids = self._select_predicted_games()

        if self.season_type == SEASON_TYPE_PLAYOFFS:
            transformers = self._build_playoff_transformers(all_games, all_team_stats, all_player_stats)
        else:
            transformers = self._build_regular_transformers()

        self.data_warnings = self._validate_season_completeness()

        self.config = ModelsConfig(
            target_col="home_win",
            test_filter=self.season,
            transformers=transformers,
            model=STRATEGY_REGISTRY[strategy](),
        )
        self.scaler = StandardScaler()

    def _select_frames(self, all_games, all_team_stats, all_player_stats) -> None:
        """Narrow the source frames to the season types this run needs."""
        frame_types = {self.season_type, self.train_season_type}
        if self.train_season_type != self.season_type:
            logger.info(
                f"Training on {self.train_season_type} games to predict {self.season_type} games"
            )

        self.df_games = all_games[all_games["season_type"].isin(frame_types)].copy()
        self.df_team_stats = all_team_stats[all_team_stats["season_type"].isin(frame_types)].copy()
        self.df_player_stats = all_player_stats[all_player_stats["season_type"].isin(frame_types)].copy()

    def _select_predicted_games(self) -> set:
        """Game ids this run predicts, pinned before GamesTransformer drops season_type."""
        predicted = self.df_games[
            (self.df_games["season"] == self.season)
            & (self.df_games["season_type"] == self.season_type)
        ]
        return set(predicted["game_id"])

    def load_data(self):
        df_games = self.db_service.read("dim_games")
        df_team_stats = self.db_service.read("fct_team_stats")
        df_player_stats = self.db_service.read("fct_player_stats")
        df_teams = self.db_service.read("dim_teams")
        # Resolved per game by the transformer, so it needs no season_type filtering below.
        df_team_strength = self.db_service.read("mart_team_strength")
        # Per team-game and keyed on game_id, so likewise.
        df_schedule_load = self.db_service.read("mart_team_schedule_load")
        # Regular season only by construction, and resolved per game by the transformer.
        df_player_value = self.db_service.read("mart_player_value")
        # Game-log derived, so it dates a past roster. Only ever read for played games.
        df_roster_history = self.db_service.read("dim_rosters")
        # Present-day snapshot, which is the point: it knows a signing before they play.
        df_current_roster = self.db_service.read("teams_roster")

        return (
            df_games, df_team_stats, df_player_stats, df_teams, df_team_strength,
            df_schedule_load, df_player_value, df_roster_history, df_current_roster,
        )

    def _build_regular_transformers(self) -> list:
        games_transformer = GamesTransformer(df_games=self.df_games)
        team_games_df = games_transformer.transform()

        boxscore_transformer = BoxscoreTransformer(df_games=team_games_df, df_boxscore=self.df_team_stats)
        boxscore_model_df = boxscore_transformer.transform()

        # Each transformer feeds the next, and build() keeps only the last one's frame.
        players_transformer = PlayersTransformer(
            model_df=boxscore_model_df,
            df_player_stats=self.df_player_stats,
            df_games=self.df_games,
        )

        team_strength_transformer = TeamStrengthTransformer(
            model_df=players_transformer.transform(),
            df_team_strength=self.df_team_strength,
            df_games=self.df_games,
        )

        schedule_load_transformer = ScheduleLoadTransformer(
            model_df=team_strength_transformer.transform(),
            df_schedule_load=self.df_schedule_load,
        )

        return [
            games_transformer,
            boxscore_transformer,
            players_transformer,
            team_strength_transformer,
            schedule_load_transformer,
            RosterValueTransformer(
                model_df=schedule_load_transformer.transform(),
                df_player_value=self.df_player_value,
                df_roster_history=self.df_roster_history,
                df_current_roster=self.df_current_roster,
                df_games=self.df_games,
            ),
        ]

    def _build_playoff_transformers(self, all_games: pd.DataFrame, all_team_stats: pd.DataFrame, all_player_stats: pd.DataFrame) -> list:
        regular_games = all_games[(all_games["season_type"] == SEASON_TYPE_REGULAR) & (all_games["season"] == self.season)].copy()
        regular_team_stats = all_team_stats[
            (all_team_stats["season_type"] == SEASON_TYPE_REGULAR) & (all_team_stats["season"] == self.season)
        ].copy()
        all_playoff_games = all_games[all_games["season_type"] == SEASON_TYPE_PLAYOFFS].copy()

        playoff_transformer = PlayoffBoxscoreTransformer(
            df_games=self.df_games,
            df_boxscore=self.df_team_stats,
            df_regular_games=regular_games,
            df_regular_boxscore=regular_team_stats,
            df_all_playoff_games=all_playoff_games,
        )
        boxscore_model_df = playoff_transformer.transform()

        # Star ratings come off regular-season play only - playoffs are too thin a sample.
        # Appending the playoff schedule gives each playoff game a row to rate.
        regular_player_stats_all_seasons = all_player_stats[all_player_stats["season_type"] == SEASON_TYPE_REGULAR].copy()
        regular_games_all_seasons = all_games[all_games["season_type"] == SEASON_TYPE_REGULAR].copy()
        players_schedule = pd.concat([regular_games_all_seasons, self.df_games], ignore_index=True)

        players_transformer = PlayersTransformer(
            model_df=boxscore_model_df,
            df_player_stats=regular_player_stats_all_seasons,
            df_games=players_schedule,
        )

        team_strength_transformer = TeamStrengthTransformer(
            model_df=players_transformer.transform(),
            df_team_strength=self.df_team_strength,
            df_games=players_schedule,
        )

        return [
            playoff_transformer,
            players_transformer,
            team_strength_transformer,
            ScheduleLoadTransformer(
                model_df=team_strength_transformer.transform(),
                df_schedule_load=self.df_schedule_load,
            ),
        ]

    def _played_game_ids(self) -> set:
        return set(self.df_games.loc[self.df_games["home_wl"].notna(), "game_id"])

    def _validate_season_completeness(self) -> list[str]:
        """Warn if `self.season` has missing or unplayed games before treating it as
        finished; neither is visible from the model's own features."""
        warnings = []
        season_games = self.df_games[
            (self.df_games["season"] == self.season)
            & (self.df_games["season_type"] == self.season_type)
        ]
        # team_id 0 is an unresolved schedule slot, not a data gap
        real_games = season_games[(season_games["home_team_id"] != 0) & (season_games["away_team_id"] != 0)]

        unplayed = real_games[real_games["home_wl"].isna()]
        if len(unplayed) > 0:
            warnings.append(
                f"{len(unplayed)} {self.season_type} game(s) in {self.season} have no recorded result yet "
                f"(e.g. {unplayed['game_id'].iloc[0]}) - excluded from evaluation rather than treated as a loss."
            )

        if self.season_type == SEASON_TYPE_REGULAR:
            counts = pd.concat([real_games["home_team_id"], real_games["away_team_id"]]).value_counts()
            if len(counts) > 0:
                expected = counts.max()
                short = counts[counts < expected]
                if len(short) > 0:
                    team_names = self.df_teams.drop_duplicates("team_id", keep="last").set_index("team_id")["team_name"]
                    details = ", ".join(f"{team_names.get(tid, tid)} ({n}/{expected})" for tid, n in short.items())
                    warnings.append(
                        f"{len(short)} team(s) have fewer than {expected} recorded {self.season} games - "
                        f"dim_games looks incomplete for them: {details}"
                    )

        for w in warnings:
            logger.warning(w)

        return warnings

    def build(self):
        for t in self.config.transformers:
            model_df = t.transform()

        # round/game_in_series are shared context, not home-vs-away differentials
        diff_cols = [c for c in model_df.columns if c.startswith("diff_")]
        context_cols = [c for c in ("round", "game_in_series") if c in model_df.columns]
        feature_cols = diff_cols + context_cols
        target_col = self.config.target_col

        is_predicted = model_df["game_id"].isin(self.predicted_game_ids)

        is_played = model_df["game_id"].isin(self._played_game_ids())

        # Without is_played, GamesTransformer's `wl == "W"` scores an unplayed game as a loss.
        if self.mode == MODE_BACKTEST:
            train_df = model_df[~is_predicted & is_played].reset_index(drop=True)
            eval_df = model_df[is_predicted & is_played].reset_index(drop=True)
            y_eval = eval_df[target_col]
        else:
            train_df = model_df[is_played].reset_index(drop=True)
            eval_df = model_df[is_predicted & ~is_played].reset_index(drop=True)
            y_eval = None

        X_train, y_train = train_df[feature_cols], train_df[target_col]
        X_eval = eval_df[feature_cols]
        eval_ids = eval_df[["game_id", "season"]]

        logger.info(f"train: {X_train.shape}  eval/predict ({self.mode}): {X_eval.shape}")

        return X_train, y_train, X_eval, y_eval, eval_ids

    def train(self) -> TrainResult:
        X_train, y_train, X_eval, y_eval, eval_ids = self.build()


        X_train_s = self.scaler.fit_transform(X_train)

        model = self.config.model
        model.fit(X_train_s, y_train)

        if len(X_eval) > 0:
            X_eval_s = self.scaler.transform(X_eval)
            proba = model.predict_proba(X_eval_s)[:, 1]
            pred = (proba >= 0.5).astype(int)
        else:
            # nothing left to predict, e.g. live mode on a completed season
            proba = np.array([])
            pred = np.array([], dtype=int)

        metrics = None
        if self.mode == MODE_BACKTEST:
            # Baseline to beat: always pick the home team. Home advantage makes it > 50/50.
            naive_pred = np.ones(len(y_eval))
            naive_proba = np.full(len(y_eval), y_train.mean())
            _report("naive (home always)", y_eval, naive_pred, naive_proba)
            metrics = _report(type(model).__name__, y_eval, pred, proba)
        else:
            logger.info(f"{type(model).__name__:20s} produced {len(pred)} predictions for unplayed {self.season} games")

        predictions = eval_ids.copy()
        predictions["actual_home_win"] = y_eval.values if y_eval is not None else None
        predictions["home_win_probability"] = proba
        predictions["predicted_home_win"] = pred.astype(bool)
        predictions["season"] = self.season
        predictions["season_type"] = self.season_type

        team_names = self.df_teams.drop_duplicates("team_id", keep="last").set_index("team_id")["team_name"]

        predictions = predictions.merge(self.df_games[["game_id", "game_date", "home_team_id", "away_team_id"]], on="game_id")
        predictions["home_team_name"] = predictions["home_team_id"].map(team_names)
        predictions["away_team_name"] = predictions["away_team_id"].map(team_names)
        predictions["matchup"] = predictions["home_team_name"] + " vs " + predictions["away_team_name"]
        predictions["predicted_winner"] = np.where(
            predictions["predicted_home_win"], predictions["home_team_name"], predictions["away_team_name"]
        )

        games_seen = pd.concat([predictions["home_team_name"], predictions["away_team_name"]]).value_counts()
        wins = predictions["predicted_winner"].value_counts()

        # Indexed on every team that appears, not on the predicted winners: a team never
        # favoured in any game would otherwise drop out of the table altogether.
        teams = pd.Series(games_seen.index, name="team")
        predicted_df = pd.DataFrame({"team": teams, "wins": teams.map(wins).fillna(0).astype(int)})
        predicted_df["loss"] = teams.map(games_seen).astype(int) - predicted_df["wins"]
        predicted_df["season_type"] = self.season_type
        predicted_df["season"] = self.season
        predicted_df = predicted_df.sort_values("wins", ascending=False).reset_index(drop=True)

        return TrainResult(model=model, metrics=metrics, predictions=predictions, season_record=predicted_df, warnings=self.data_warnings)
