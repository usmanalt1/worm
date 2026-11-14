FROM python:3.12-slim

LABEL org.opencontainers.image.authors="UA"

COPY --from=ghcr.io/astral-sh/uv:0.13.8 /uv /usr/local/bin/uv

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Europe/London \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_DIR=/nba_app \
    USER_NAME=automater \
    AWS_DEFAULT_REGION=eu-west-2 \
    FLASK_APP=api/app.py \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH=/opt/venv/bin:$PATH

# Install system dependencies (including build tools for Python packages)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        apt-transport-https \
        ca-certificates \
        awscli \
        build-essential \
        default-mysql-client \
        default-libmysqlclient-dev \
        gcc \
        git \
        libpq-dev \
        libmariadb-dev \
        openssh-client \
        pkg-config \
        python3-dev \
        vim \
        nano && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m $USER_NAME -s /bin/bash

# Create app directory
RUN mkdir $APP_DIR && chown $USER_NAME:$USER_NAME $APP_DIR
WORKDIR $APP_DIR

# /opt/venv, not $APP_DIR/.venv: compose bind-mounts the host checkout over $APP_DIR
# at runtime, which would shadow a project-local venv with the host's macOS one.
COPY --chown=$USER_NAME:$USER_NAME pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY --chown=$USER_NAME:$USER_NAME . .

# Switch to non-root user
USER $USER_NAME

# Make entrypoint executable
RUN chmod +x  ./scripts/entrypoint.sh

EXPOSE 5000

CMD ["python", "backend/src/manage.py", "runserver", "0.0.0.0:8000"]