FROM python:3.14-slim-bookworm AS builder

WORKDIR /app


# Install dependencies
RUN apt update && apt --no-install-recommends install -y build-essential gcc git libpq-dev

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy workspace configuration from root
COPY .git uv.lock pyproject.toml ./
COPY jobbergate-api ./jobbergate-api

# Install only jobbergate-api and its dependencies
RUN uv sync --frozen --no-editable --no-python-downloads --package jobbergate-api --group dev


FROM python:3.14-slim-bookworm AS runner

WORKDIR /app

RUN apt update \
    && apt --no-install-recommends install -y build-essential gcc libpq-dev \
    && apt-get clean \
    && groupadd --system appuser \
    && useradd --system --create-home --gid appuser appuser

# Copy files before switching user
COPY --from=builder /app/.venv .venv
COPY --from=builder /app/jobbergate-api/alembic alembic

ENV PATH="/app/.venv/bin:$PATH"

# Change ownership of /app to the new user and switch to it
RUN chown -R appuser:appuser /app
USER appuser

CMD ["uvicorn", "jobbergate_api.main:app", "--host", "0.0.0.0", "--port", "80"]
