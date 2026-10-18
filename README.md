# Worm — NBA Prediction Lab

Worm collects NBA data every night, models it into a warehouse, rates every team with
Elo, predicts every game left in the season, and serves the whole thing through a React
app. It also grades itself: each prediction is frozen before tip-off and scored once the
game finishes, so the model's record is a measured number rather than a claim.

- **Frontend** — React 19 + Vite + Mantine, deployed to Cloudflare Workers
- **API** — Django 4.2 + Django Ninja (ASGI), deployed to Cloud Run
- **Warehouse** — Postgres (Neon in production), modelled with dbt
- **Orchestration** — Dagster assets, executed by GitHub Actions
- **Model** — scikit-learn, 26 features in the regular season, 30 in the playoffs

---

## What the app does

Five pages, behind a JWT login:

| Page | Route | What it shows |
|---|---|---|
| **Home** | `/` | The upcoming slate with win probabilities, last night's results, season and team leaders, hot/cold form, most-improved, model pulse and strategy comparison, league trends, postseason state |
| **Can of Worms** | `/view` | Stats explorer — players, teams, seasons, basic and advanced, filterable and sortable |
| **Wormalytics** | `/analytics` | Build-your-own analytics. Pick a scope (player / team / season) and a season, choose metrics, and get a scatter/quadrant, four-factor bars, trend lines, leaderboards and standings. Presets cover the common views |
| **Wormhole** | `/predictions` | Run a backtest for a season, season type and strategy. Reports accuracy, log loss, Brier score and AUC against a naive "always pick home" baseline, plus the model's predicted standings |
| **Ask Worm** | `/nbai` | Natural-language questions. Claude writes read-only SQL against the marts through a tool loop and answers from the rows it gets back |

### The prediction model in one paragraph

One class, `ModelTraner`, runs in two modes. In **backtest** mode it holds out a finished
season, trains on every other season, and scores itself against reality. In **live** mode
it trains on every game played so far — this season included — and predicts the games
with no result yet. Both modes build features identically, which is the point: a backtest
that measured a richer feature set than the live run would be measuring a model that never
ships. Features are all home-minus-away differences: season-to-date form blended against
last season, star-player counts, Elo and opponent-adjusted margin, travel and schedule
congestion, and the minutes-weighted value of each rotation.

The full write-up — every feature, how it resolves for a game that has not been played,
where the leakage traps are — is in
[backend/src/services/ml_model/model_documentation/README.md](backend/src/services/ml_model/model_documentation/README.md),
with worked numeric examples in
[FEATURES.md](backend/src/services/ml_model/model_documentation/FEATURES.md). Read those
before changing anything in `services/ml_model`.

---

## Running locally

### Prerequisites

- Docker and Docker Compose
- A `.env` at the repo root (see below)
- Python 3.9 only if you want to run dbt or Dagster outside the containers

### Environment

Compose passes the root `.env` into the backend and both Dagster containers. The
variables that matter locally:

| Variable | Local value | Notes |
|---|---|---|
| `DJANGO_SECRET_KEY` | any string | Required — settings will not import without it |
| `JWT_SIGNING_KEY` | any string | Required, same |
| `DEBUG` | `true` | Also switches logging to DEBUG |
| `ENVIRONMENT` | `local` | |
| `STORAGE` | `local` | `gcs` and `az` are the other backends |
| `FILE_PATH_PARENT_NAME` | `nba-ua-dev-bucket` | Where the local-disk storage path writes parquet |
| `FILE_FORMAT` | `parquet` | |
| `DAGSTER_HOME` | `/nba_app/dagster_home` | Must stay the **container** path |
| `ANTHROPIC_API_KEY` | your key | Only needed for Ask Worm |
| `LLM_DB_USER` / `LLM_DB_PASSWORD` | `llm_readonly` / `llm_readonly` | Migration 0014 creates this role; dbt's `on-run-end` grants to it |
| `DATABASE_URL` | **leave unset** | Set, it switches Django to the Neon production database |

`DATABASE_URL` unset is what keeps local runs on the compose Postgres. Setting it points
the local backend at production.

### Start everything

```bash
docker compose up --build
```

| Service | Port | What it is |
|---|---|---|
| `nba_app_frontend` | 5173 | Vite dev server, proxies `/api` to the backend |
| `nba_app_backend` | 8000 | Django dev server |
| `dagster-webserver` | 3000 | Dagster UI — materialise assets, inspect runs |
| `dagster-daemon` | — | Runs the schedules. Without it the nightly cron never fires |
| `postgres-host` | 5432 | The warehouse. `backend_db` + a `dbt_nba` database |
| `redis` | 6379 | Model run cache |
| `mysql-host` | 3307 | Legacy. Nothing reads it, but the backend still waits on its healthcheck |

### Apply migrations

```bash
docker compose exec nba_app_backend python backend/src/manage.py migrate
```

Run this before the first dbt build — dbt's `on-run-end` grants to `llm_readonly`, and
migration 0014 is what creates that role.

### Load some data

The pipeline is the supported path. From the Dagster UI at `http://localhost:3000`,
materialise the `nightly_pipeline` job, or from the shell:

```bash
docker compose exec dagster-webserver \
  dagster job execute -f /nba_app/dagster/definitions.py -d /nba_app/dagster -j nightly_pipeline
```

That collects the in-progress season, loads it into Postgres, builds the dbt marts,
walks the Elo ratings and re-predicts the remaining slate. For backfilling older seasons
there are collection endpoints on the API — `/api/nba/collect/season/{season_year}` and
`/api/nba/collect/season/{season_year}/{seasons}/team_roster={bool}` — which write parquet
to object storage, followed by `/api/nba/load_to_postgres`.

### dbt on its own

```bash
docker compose exec dagster-webserver bash -lc \
  'cd /nba_app/pipeline_nba && dbt build --target container_postgres'
```

Targets in [pipeline_nba/profiles.yml](pipeline_nba/profiles.yml):

| Target | Points at |
|---|---|
| `local` | The host DuckDB file, `nba_dataset.duckdb` |
| `container` | The same DuckDB file at the bind-mount path |
| `container_postgres` | The compose Postgres, by service name. **This is what the Dagster containers use** |
| `dev` | The compose Postgres via `localhost`, for running dbt from the host |
| `neon` | Production, used by the nightly workflow |
| `bigquery` | The `nba-ua-dev` analytics mirror |

### Visit it

`http://localhost:5173`. Register a user on `/auth` — every other route redirects there
without a token.

---

## Production architecture

```
                 ┌─────────────────────────────┐
  browser ─────► │ Cloudflare Worker  "worm"   │   static assets, SPA routing
                 │ React build from ./dist     │
                 └──────────────┬──────────────┘
                                │ VITE_API_URL
                                ▼
                 ┌─────────────────────────────┐
                 │ Cloud Run  "nba-api"        │   uvicorn ASGI, europe-west2
                 │ Django Ninja, JWT auth      │   2 CPU / 2Gi / 900s
                 └───┬──────────────┬──────────┘
                     │              │
          ┌──────────▼───┐   ┌──────▼────────┐
          │ Neon Postgres│   │ Redis         │   model run cache, 26h TTL
          │ nba_marts.*  │   │               │
          │ public.*     │   └───────────────┘
          └──────▲───────┘
                 │
                 │ writes
   ┌─────────────┴───────────────────────────────────┐
   │ GitHub Actions: nightly-pipeline                │
   │   dagster job execute -j nightly_pipeline       │
   │                                                 │
   │   latest_nba_data     stats.nba.com ─► GCS      │
   │   postgres_raw_tables GCS ─► public.*           │
   │   dbt_marts           dbt build ─► nba_marts.*  │
   │   team_strength       Elo walk ─► mart_team_…   │
   │   live_predictions    model ─► Redis + history  │
   └─────────────────────────────────────────────────┘
                 │
                 ▼
          GCS nba-ua-prod-bucket          raw parquet, one prefix per run
          BigQuery nba-ua-dev             separate analytics mirror, API never reads it
```

### Pieces

- **Frontend** — Cloudflare Worker named `worm`, serving `./dist` as static assets.
  `not_found_handling: single-page-application` is what makes deep links work.
  Config is declared in [frontend/wrangler.jsonc](frontend/wrangler.jsonc) rather than
  left to wrangler's framework detection, which would regenerate it every build.
  Built and deployed by Cloudflare, not by Actions. `VITE_API_URL` comes from
  [frontend/.env.production](frontend/.env.production) and must stay unset in dev, where
  the Vite proxy handles `/api`.
- **API** — Cloud Run service `nba-api` in `europe-west2`, built from the root
  [Dockerfile](Dockerfile) (which exists at the root only because
  `gcloud run deploy --source .` looks there). It runs uvicorn, not `runserver`: the
  model and LLM routers expose async endpoints.
- **Database** — Neon Postgres. `conn_max_age=0` and `ssl_require=True`: Neon drops idle
  connections, so a persistent one is dead on reuse, and its pooler makes a fresh
  connection per request cheap.
- **Cache** — managed Redis via `REDIS_URL`. Nightly runs land under
  `model_run_cache_key(...)` with a 26-hour TTL — long enough that one run survives until
  the next replaces it, short enough that a failed pipeline serves nothing rather than
  yesterday's slate. User backtests cache separately, per user, for 24 hours.
- **Object storage** — GCS bucket `nba-ua-prod-bucket`, project `nba-ua-prod`. The GCS
  clients take a keyfile path, so the nightly workflow writes the service-account secret
  to disk before any asset touches storage.
- **Egress** — `stats.nba.com` blackholes GitHub's runner IPs, so the nightly sets
  `NBA_PROXY`. Unset, requests go direct, which is why local runs are unaffected.

### The nightly pipeline

Defined as Dagster assets in [dagster/assets.py](dagster/assets.py) and wired into jobs
in [dagster/definitions.py](dagster/definitions.py):

| Asset | Kind | Does |
|---|---|---|
| `latest_nba_data` | nba_api | Collects the in-progress season into object storage, returns a `run_id` |
| `postgres_raw_tables` | postgres | Upserts that run's parquet into the raw `public.*` tables |
| `dbt_marts` | dbt | `dbt build` — not `run`, so a failing test stops downstream models |
| `team_strength` | python | Walks Elo and opponent-adjusted form over every completed game into `mart_team_strength` |
| `live_predictions` | python | Predicts every unplayed game per strategy and season type, into Redis and `model_prediction_history` |
| `backtest_scorecard` | python | Scores every strategy against a finished season |
| `bigquery_tables` | bigquery | Mirrors a collected run into BigQuery. Analytics only |

Three jobs: `nightly_pipeline` (the five assets above, in order), `backtest_pipeline`
(`backtest_scorecard` alone, reusing whatever marts the last nightly left), and
`bigquery_mirror`.

`live_predictions` takes `team_strength` as an input it never reads, purely to force the
ratings to rebuild first. Predicting before the rebuild would score tonight's games with
ratings that ignore last night's results.

All three jobs use `in_process_executor`: the assets are sequential, so forking only
re-imports Django and sklearn per child, and the multiprocess executor SIGBUSes in the
container.

**Scheduling, as it actually stands.** The Dagster `ScheduleDefinition` fires at 09:00
Europe/London — 04:00 ET, after the last west-coast game — and runs in compose, where
`dagster-daemon` is there to execute it. In production there is no daemon: the nightly
runs as a GitHub Actions workflow, and its cron was removed, so
[.github/workflows/nightly.yml](.github/workflows/nightly.yml) is **`workflow_dispatch`
only** — someone has to trigger it. Re-adding the cron there is the one-line change.

It runs as a single job on purpose: `latest_nba_data` writes parquet to the workspace and
`postgres_raw_tables` reads it back off local disk, so splitting them across jobs loses
the handoff.

### Warehouse layers

[pipeline_nba/](pipeline_nba/), staging → intermediate → marts, plus semantic views:

- **staging** — one model per raw ingest table: teams, players, rosters, team and player
  game logs, game schedule, season record, advanced season stats, player awards, draft
  history
- **intermediate** — `int_home_away_games`, `int_players_rosters`,
  `int_player_team_history`
- **marts** — `dim_games` (the spine, including *scheduled* games with null scores, which
  is what makes live prediction possible), `dim_teams`, `dim_players`, `dim_rosters`,
  `dim_seasons`, `dim_player_awards`, `dim_draft_picks`, `fct_team_stats`,
  `fct_player_stats`, `fct_advanced_team_season_stats`,
  `fct_advanced_player_season_stats`, `mart_team_game_form`, `mart_player_game_form`,
  `mart_player_value`, `mart_player_volatility`, `mart_team_schedule_load`
- **semantic views** — `view_team_stats`, `view_player_stats`

`mart_team_strength` is the exception: it is written by a Python asset, not dbt.

The Django models the API serves are `managed = False` views onto `nba_marts.*`, which is
why the warehouse is Postgres and not BigQuery.

### API surface

Mounted under `/api` by [backend/src/api/api.py](backend/src/api/api.py):

| Router | Prefix | Covers |
|---|---|---|
| auth | `/api/auth/` | Register, login, `/me`, plus the Ninja JWT controller |
| nba | `/api/nba/` | Collection and load operations — seasons, tables, schedules, awards, advanced stats; loads into Postgres, BigQuery or DuckDB |
| db | `/api/nba/db/` | Reference and stats reads — season and team lists, player lookup, season player/team stats basic and advanced, team colours |
| model | `/api/nba/model/` | Train/backtest, cached runs, per-user last run, prediction history, model list |
| analytics | `/api/nba/analytics/` | Average player and team stats, most improved, hot and cold, league trends, player volatility, team context |
| llm | `/api/nba/llm/` | `POST /ask`, plus the cached conversation |

Everything except register and login requires a JWT.

### CI/CD

| Workflow | Trigger | Does |
|---|---|---|
| [deploy.yml](.github/workflows/deploy.yml) | push to `main` touching `backend/`, `dagster/`, `pipeline_nba/`, `requirements.txt` or `Dockerfile` | Deploys `nba-api` to Cloud Run via workload identity federation |
| [nightly.yml](.github/workflows/nightly.yml) | manual | Runs `nightly_pipeline` against Neon and GCS, then emails the outcome |
| [migrations.yml](.github/workflows/migrations.yml) | manual | Applies or rolls back Django migrations, printing before/plan/after into the job summary |
| [django-checks.yml](.github/workflows/django-checks.yml) | PRs touching `backend/` | Fails if a model changed without a matching migration |

**Deploys do not migrate.** `deploy-api` deliberately skips it, so a schema change has to
be applied from the migrations workflow *before* the code that needs it ships. A rollback
there needs the target retyped into `confirm_target`, because unapplying a real table
drops it and its rows — and migrations 0018 and 0019 run irreversible SQL, so Django
cannot unapply past 0020.

---

## Repo layout

```
backend/src/
  api/              Django Ninja routers — api, db, model, analytics, llm, auth
  app/              settings, urls, models (mostly managed=False views), migrations
  config/           pydantic-settings Settings + logger
  services/
    data_collection/  nba_api collection and the build service
    db/               upserts, parquet loads, async helpers
    ml_model/         features/, models/, repository/, model_documentation/
    ratings/          Elo and opponent-adjusted form
    analytics/        season stats, team context, volatility
    llm/              query engine, SQL runner, system prompt, tools
    injuries/         injury feed
    notifications/    email
    object_storage/   local, GCS, Azure
    warehouse_storage/ DuckDB, BigQuery
    redis/            client and key constants
dagster/            assets, definitions, alerts, season helpers
pipeline_nba/       dbt project — models, seeds, macros, tests, ci profile
frontend/src/       React app — components/, hooks/, lib/, context/, types/
docker/             compose Dockerfiles and the Postgres init script
scripts/            pipeline_alert.py
Dockerfile          Cloud Run image
docker-compose.yml  local stack
```

---

## Releases

### v1.0 — 10 October 2026

The first deployable version: 149 commits, PRs #1–#38. Everything from an empty repo to a
live app.

**Data platform**
- NBA collection off `nba_api` into object storage, with local, GCS and Azure
  backends, one parquet prefix per run
- Raw Postgres load with upsert semantics, keyed per run
- dbt project — staging, intermediate and marts for games, teams, players, rosters,
  seasons, awards, basic and advanced season stats, team and player game form, plus
  semantic views
- Dagster assets and jobs for the nightly pipeline, the backtest and a BigQuery mirror
- Optional DuckDB and Snowflake targets alongside Postgres and BigQuery

**Model**
- `ModelTraner` with the backtest/live split, `logistic_regression` and `random_forest`
  strategies
- The games, boxscore, players and playoff-boxscore transformers — season-to-date form
  blended against last season, star counts, rest and back-to-backs, and a separate
  playoff chain with series state and playoff history
- Metrics against a naive home-team baseline: accuracy, log loss, Brier, AUC
- `model_prediction_history`, which freezes a prediction once its game has a result, and
  `best_strategy` ranking on Brier score
- Season completeness validation, surfaced as warnings in the UI

**API and app**
- Django Ninja API with JWT auth and user registration
- Redis caching of model runs, scoped per user
- The five pages — Home, Can of Worms, Wormalytics, Wormhole, Ask Worm — in React 19 and
  Mantine, with the Worm theme
- Ask Worm: Claude writing read-only SQL against the marts through a tool loop
- Regular season and playoffs separated throughout, in the model and in the UI

**Deployment**
- Cloud Run API on an ASGI server, Cloudflare Workers frontend with SPA routing
- Neon Postgres, managed Redis, GCS production bucket
- Build config driven by environment, defaulting to compose
- Proxy support for `stats.nba.com`, which blackholes GitHub runner IPs

### v1.1 — 18 October 2026

PRs #39–#46. 88 files, ~5,200 insertions. Mostly new model features and a rebuilt
analytics page.

**New model features** — the regular-season feature set went from 18 to 26
- **Elo and opponent-adjusted form** (`mart_team_strength`, migration 0021). Ratings start
  at 1500, carry over between seasons damped at 0.75, and run continuously through the
  playoffs. Stored as both `_pre` and `_post` so a live prediction can inherit the last
  rated game's strength instead of lagging a full rating move behind
- **Schedule load** (`mart_team_schedule_load`, a `team_locations` seed, a haversine
  macro): travel kilometres, time zones crossed, altitude gain, games in the previous
  seven days, road-trip depth. All known months in advance, straight off the schedule
- **Roster value** (`mart_player_value`): the minutes-weighted value of each team's top 8,
  read from today's roster snapshot for unplayed games. The only feature that reacts to a
  transaction before the player takes the court. Migration 0026 re-keyed `teams_roster` on
  `(player_id, season_id)` so a traded player moves rather than gaining a row
- Fixed the form warm-up that had been silently dropping 48 games from every season's
  backtest, making the standings read 79 games instead of 82

**New data**
- Draft history → `dim_draft_picks` (migration 0022)
- Player injury feed and `PlayerInjury` model (migrations 0023, 0024). History starts
  18 October 2026 — not yet enough snapshots to build an availability feature from
- Player volatility → `mart_player_volatility` (migration 0025)
- A dbt test asserting `dim_games` covers `team_logs`

**Wormalytics, rebuilt**
- Scope bar — player / team / season, with a selectable season
- A metric picker that composes a custom view, and preset views on a rail
- New chart primitives: scatter/quadrant, trend lines, four-factor bars
- Metric leaderboards and season standings
- New analytics endpoints: hot and cold, league trends, player volatility, team context
- Navbar rework, team colours wired through a provider, mobile rendering

**Operations**
- Email alerting on pipeline outcome — Dagster sensors for daemon runs, plus a
  `scripts/pipeline_alert.py` step for Actions runs, where sensors cannot fire
- The manual migrations workflow, with plan output and a confirmed-rollback guard
- The missing-migrations PR check
- Neon connection pooling fix — connections are now closed rather than held
- The model documentation under
  [model_documentation/](backend/src/services/ml_model/model_documentation/), replacing the
  old single README

---

## Things that bite

- **Stale ratings.** `mart_team_strength` is written by a Python asset, not dbt. Rebuild
  `dim_games` by hand and the ratings do not follow — the model keeps using the old ones.
  Re-materialise `team_strength`.
- **A null feature drops the whole game.** Four of the five transformers drop a row rather
  than fill it. A new feature that can be null will quietly shrink the evaluated set until
  you decide which it is. The per-transformer `dropped N rows` log lines name the culprit.
- **Wormhole hydrates from cache on load.** After changing anything upstream you have to
  press Run again; a plain reload shows the previous run.
- **The local DB host is a container name.** `app/settings.py` falls back to
  `nba_app-postgres-host-1`, which Compose derives from the directory name. Rename the
  checkout directory and the backend stops finding Postgres.
- **The Vite proxy targets a container name** (`http://nba_app_backend:8000`), so the dev
  server has to run inside Compose for `/api` to resolve.
- **dbt's `on-run-end` grants to `llm_readonly`.** A local `dbt build` ends in a grant
  error if migrations have not been run first, or against a DuckDB target where the role
  does not exist.
- **Compose still starts MySQL.** Nothing reads it, but `nba_app_backend` waits on its
  healthcheck, so it is on the critical path for startup.
