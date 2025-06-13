FROM python:3.11-slim-buster AS builder

WORKDIR /app

RUN apt update && apt install -y curl libpq-dev gcc

RUN pip install poetry==2.1.1

COPY ./pyproject.toml ./poetry.lock /app

RUN poetry config virtualenvs.in-project true \
    && poetry install --no-root \
    && rm -rf "$POETRY_CACHE_DIR"


FROM python:3.11-slim-buster AS runner

WORKDIR /app

RUN apt update && apt install -y curl libpq-dev gcc

COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH"

COPY ./alembic /app/alembic
COPY ./jobbergate_api /app/jobbergate_api

CMD ["uvicorn", "jobbergate_api.main:app", "--host", "0.0.0.0", "--port", "80"]
