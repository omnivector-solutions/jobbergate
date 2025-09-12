FROM python:3.11-slim-bookworm AS builder

WORKDIR /app


# Install dependencies
RUN apt update && apt --no-install-recommends install -y build-essential curl gcc libpq-dev

RUN pip install poetry==1.5.1

COPY ./pyproject.toml ./poetry.lock /app/

RUN poetry config virtualenvs.in-project true \
    && poetry install --no-root \
    && rm -rf "$POETRY_CACHE_DIR"


FROM python:3.11-slim-bookworm AS runner

WORKDIR /app

RUN apt update \
    && apt --no-install-recommends install -y build-essential gcc libpq-dev \
    && apt-get clean \
    && groupadd --system appuser \
    && useradd --system --create-home --gid appuser appuser

# Copy files before switching user
COPY --from=builder /app /app


ENV PATH="/app/.venv/bin:$PATH"


COPY ./alembic /app/alembic
COPY ./jobbergate_api /app/jobbergate_api


# Change ownership of /app to the new user and switch to it
RUN chown -R appuser:appuser /app
USER appuser

CMD ["uvicorn", "jobbergate_api.main:app", "--host", "0.0.0.0", "--port", "80"]
