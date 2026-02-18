FROM python:3.14-slim-bookworm AS builder

WORKDIR /app

RUN apt update && apt --no-install-recommends install -y git && apt-get clean

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY .git uv.lock pyproject.toml ./
COPY jobbergate-core ./jobbergate-core
COPY jobbergate-agent ./jobbergate-agent

RUN uv sync --frozen --no-editable --no-python-downloads --package jobbergate-agent --no-dev

FROM python:3.14-slim-bookworm AS runner

WORKDIR /app

RUN groupadd --system appuser \
    && useradd --system --create-home --gid appuser appuser

# Copy files before switching user
COPY --from=builder /app/.venv .venv
COPY --from=builder /app/jobbergate-agent/README.md README.md
COPY --from=builder /app/jobbergate-agent/LICENSE LICENSE

# Change ownership of /app to the new user and switch to it
RUN chown -R appuser:appuser /app
USER appuser

ENTRYPOINT ["/app/.venv/bin/jg-run"]
