FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt update && apt --no-install-recommends install -y curl \
    && groupadd --system appuser \
    && useradd --system --create-home --gid appuser appuser

RUN curl -sS --proto "=https"  https://install.python-poetry.org | \
    POETRY_HOME=/opt/poetry POETRY_VERSION=1.5.1 python && \
    ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry

COPY ./pyproject.toml ./poetry.lock ./README.md ./LICENSE /app/
COPY ./etc/entrypoint.sh /app/entrypoint.sh
WORKDIR /app

# Change ownership of /app to the new user and switch to it
RUN chown -R appuser:appuser /app
USER appuser

VOLUME /app/jobbergate_cli
VOLUME /jobbergate-core

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["/app/entrypoint.sh"]
