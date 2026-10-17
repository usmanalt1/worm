# How the prediction model works

One class, `ModelTraner`, does both jobs. The only difference is `mode`:

| | `backtest` | `live` |
|---|---|---|
| Question | how good is this model? | who wins tonight? |
| Season | a finished one | the one in progress |
| Trains on | every *other* season | every game played so far, this season included |
| Predicts | the chosen season's games, which already have results | the games with no result yet |
| Produces | accuracy / log loss / brier / auc | probabilities only, no metrics |
| Triggered by | the Predictions page, or the weekly Dagster job | the nightly Dagster job at 09:00 London |

Everything else — the data, the features, the Elo ratings — is identical. That is
deliberate: a backtest is only informative if it builds its features the same way the
live run does.

## What the model reads

`load_data` in [models/model_trainer.py](models/model_trainer.py) pulls five marts through
Django (`managed = False` views onto `nba_marts.*`):

| Table | Used for |
|---|---|
| `dim_games` | one row per game: who, when, final score. The spine. |
| `fct_team_stats` | team box scores, which become rolling form |
| `fct_player_stats` | player box scores, which become star counts |
| `dim_teams` | names for display |
| `mart_team_strength` | Elo rating and opponent-adjusted form per team per game |

Note `dim_games` includes *scheduled* games with null scores. That is what makes live
mode possible: an unplayed game is a real row with `home_wl` null.

## From a game to a feature row

Four transformers run in order, each feeding the next
([models/model_trainer.py](models/model_trainer.py), `_build_regular_transformers`):

1. **`GamesTransformer`** — splits each game into two team rows, one home, one away.
   1230 games become 2460 team-games.
2. **`BoxscoreTransformer`** — attaches each team's season-to-date averages, blended with
   last season's as a baseline while this season is thin, then folds the two team rows
   back into one row per game of home-minus-away differences.
3. **`PlayersTransformer`** — adds star-player counts per side.
4. **`TeamStrengthTransformer`** — adds the two Elo features.

The model only ever sees columns named `diff_*` (plus `round` and `game_in_series` in the
playoffs). Every feature is a difference: home minus away.

**Nothing in a row may postdate the game.** Season-to-date averages use `shift(1)`, Elo
uses the rating *before* the game, and form is also shifted. Without that, the model
would train on the answer.

## Elo and form

Built by [../ratings/team_strength_service.py](../ratings/team_strength_service.py) into
`mart_team_strength`. Two measures per team per game, each stored twice — as it stood
*before* the game, and as it stood once that game was counted:

- **`elo_pre`** / **`elo_post`** — the team's rating entering and leaving the game. Starts
  at 1500. A result moves it by how far it beat what the rating predicted, so beating a
  strong team is worth more than beating a weak one. A rating of +400 over an opponent
  means 10:1 odds.
- **`form_adj_margin`** / **`form_adj_margin_post`** — mean margin over the last 10 games
  of this season, with each margin credited for how good that opponent was at the time.
  The `_post` column includes the current game, the other does not.

A game may only ever read its own `_pre` columns — that is what keeps a result out of the
features that predict it. The `_post` pair exists for a *later* game to inherit, which is
how live mode works (below).

The model uses the differences:

```
diff_team_elo   = elo_pre(home)         - elo_pre(away)
diff_adj_margin = form_adj_margin(home) - form_adj_margin(away)
```

### A real example

Miami vs Atlanta, 12 April 2026 (`game_id` 0022501189):

| | `elo_pre` | `form_adj_margin` |
|---|---|---|
| MIA (home) | 1501.9 | -5.74 |
| ATL (away) | 1602.2 | +14.45 |

```
diff_team_elo   = 1501.9 - 1602.2  = -100.3
diff_adj_margin =  -5.74 - 14.45   =  -20.19
```

Both strongly negative: the home team was the clear underdog on rating and on recent
form. Elo alone, including the 56-point home advantage, gave Miami about a 44% chance.
Miami won 143-117. Pre-game features are honest, not clairvoyant — the point of a
backtest is to measure how often they are right across a whole season, not per game.

### Season boundaries and warm-up

Two edges worth knowing, because both bit us:

- **Elo carries over, damped.** A new season starts at `START + 0.75 * (rating - 1500)`,
  so a 1600 team opens at 1575. Rosters change, so last season is evidence, not a
  starting point.
- **Form needs 3 games** (`MIN_FORM_GAMES`). Each team's first 3 games of a season have
  no form value at all. `TeamStrengthTransformer` fills the missing *difference* with 0
  — "no form edge either way" — rather than dropping the game. It used to drop it, which
  silently removed 48 games from every season's backtest and made the standings read 79
  games instead of 82.
- **Playoffs are rated, and continuously.** `_read_games` takes
  `season_type in ('regular', 'playoffs')`. Playoff games carry the same `season`
  string as the regular season, and `CARRYOVER` only fires when that string *changes*,
  so a rating runs straight on into the postseason with no damping and keeps moving
  round to round. The 2025-26 champion went 1652.5 entering round 1 to 1731.9 by the
  conference finals. Only the next regular season regresses it — from the
  post-playoff rating, which is the most recent evidence there is.

## Backtest: how the split works

Say you backtest 2025-26 regular season. `df_games` holds every regular-season game of
every season. Two flags decide each row's job:

- `is_predicted` — this game is in the season under test
- `is_played` — this game has a result

```python
train_df = model_df[~is_predicted & is_played]   # all other seasons
eval_df  = model_df[is_predicted & is_played]    # 2025-26, scored against reality
```

Real numbers from a 2025-26 run: 11,933 feature rows in total, 1,230 of them 2025-26, so
the model trains on roughly 10,700 games from 2017-18 through 2024-25 and is scored on
the 1,230 it has never seen. The season under test is held out entirely — that is what
makes the metric meaningful.

`train()` then reports two lines: the model, and a naive "always pick the home team"
baseline. If the model cannot beat the baseline, it is not earning its keep.

The standings table in the UI (`season_record`) is the model's **predicted** record, not
the real one — wins counted from `predicted_winner`. If a team shows fewer than 82 games
there, games are being dropped somewhere in the transformer chain.

## Live: how the split works

Same code, one flag flipped:

```python
train_df = model_df[is_played]                   # everything played, this season too
eval_df  = model_df[is_predicted & ~is_played]   # every game still to come
y_eval   = None                                  # nothing to score against
```

Two things surprise people:

**It predicts the whole rest of the season, not tonight's slate.** `eval_df` is every
unplayed game of that season type. The 2026-27 regular season currently has 1,200 stored
predictions, running from 20 October 2026 to 11 April 2027.

**Every future game shares one rating snapshot per team.** `mart_team_strength` only has
rows for *completed* games, so a game in April has no rating row of its own.
[features/team_strength_transformer.py](features/team_strength_transformer.py) resolves
each team-game in one of two ways, and the distinction is the whole ballgame:

| the game is | it reads | why |
|---|---|---|
| rated (played) | its own `elo_pre` / `form_adj_margin` | pre-game by construction, so no leakage |
| not rated (being predicted) | the last rated game's `elo_post` / `form_adj_margin_post` | the team's strength *now*, last result included |

Reading `elo_pre` for an unrated game would discard the team's most recent result and lag
by a full rating move — 8.45 points on average, up to 41.7. That is why the mart publishes
both halves of each pair.

Two more rules on the inherited path:

- If the last rated game is in an **earlier season**, the inherited Elo is regressed
  through `carry_into_new_season` first, so opening night uses 1575 for a 1600 team rather
  than 1600.
- Form is a within-season window, so it is **blanked** across a season boundary rather
  than inherited. `_merge_differentials` then fills the missing difference with 0, the
  same treatment the first three games of any season get.

So a game three weeks out is predicted with today's numbers, and tomorrow's pipeline
re-predicts it with tomorrow's.

That is the whole reason for the dependency in [../../../../dagster/assets.py](../../../../dagster/assets.py):

```python
def live_predictions(context, config, dbt_marts: dict, team_strength: dict):
```

`live_predictions` takes `team_strength` as an input it does not otherwise use, purely to
force the ratings to be rebuilt first. Predicting before the rebuild would score tonight's
games with ratings that ignore last night's results.

## Where it runs and where the output goes

The nightly job at 09:00 London (04:00 ET, after the last west-coast game):

```
latest_nba_data      NBA API      -> object storage
postgres_raw_tables  storage      -> Postgres public.*
dbt_marts            dbt build    -> nba_marts.*          (dim_games rebuilt here)
team_strength        Elo walk     -> nba_marts.mart_team_strength
live_predictions     ModelTraner  -> Redis + model_prediction_history
```

Live predictions land in two places:

- **Redis**, under `model_run_cache_key(...)`, TTL 26 hours — long enough that one run
  survives until the next replaces it, short enough that a failed pipeline serves nothing
  rather than yesterday's slate.
- **`model_prediction_history`** in Postgres, one row per game, upserted. An unplayed
  game's prediction is refreshed every night; once the game has a result,
  `persist_predictions` skips it, freezing what the model actually said before tip-off.
  Overwriting it later would be hindsight. That table is what grades the model over time
  and what `best_strategy` reads to pick which run the homepage opens on.

Backtests from the Predictions page cache per user, under
`user_run_cache_key(user_id, ...)` with a 24-hour TTL. **The page hydrates from that cache
on load**, so after changing anything upstream you must press Run again — a plain reload
shows the previous run.

There is also a weekly `backtest_pipeline` (Mondays 11:00, stopped by default, useful out
of season or after a model change). It selects `backtest_scorecard` alone, so it reuses
whatever marts and ratings the last nightly left behind rather than rebuilding them.

## Things that bite

- **Stale ratings.** `mart_team_strength` is rebuilt by a Python asset, not dbt. If you
  rebuild `dim_games` by hand, the ratings do not follow and the model keeps using the
  old ones. Re-materialise `team_strength`.
- **A dropped feature drops the whole game.** `TeamStrengthTransformer` still drops a row
  with no `diff_team_elo`. Any new feature that can be null will quietly shrink the
  evaluated set unless you decide what null means, as form does with 0.
- **Watch the warning list.** `_validate_season_completeness` checks for unplayed games
  and for teams with fewer games than their peers, and the result carries `warnings`
  through to the UI. A team short of 82 games means `dim_games` lost something upstream.
- **Preseason trains on regular-season games.** `TRAIN_SEASON_TYPE` maps preseason to
  regular, because preseason has no history of its own to learn from.
