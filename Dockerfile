# Cloud Run image. Local compose builds docker/backend.Dockerfile instead; this one
# exists at the root because `gcloud run deploy --source .` only looks here.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.8 /uv /usr/local/bin/uv

# The venv lives outside WORKDIR so a bind mount over /nba_app cannot shadow it.
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/nba_app/backend/src \
    DJANGO_SETTINGS_MODULE=app.settings \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH=/opt/venv/bin:$PATH

WORKDIR /nba_app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        default-libmysqlclient-dev \
        gcc \
        libmariadb-dev \
        pkg-config \
        python3-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

RUN useradd -m automater && chown -R automater:automater /nba_app
USER automater

# ASGI, not runserver: the model and llm routers expose async endpoints. Cloud Run
# injects PORT, so this has to be the shell form to expand it.
CMD exec uvicorn app.asgi:application --host 0.0.0.0 --port ${PORT:-8080}
