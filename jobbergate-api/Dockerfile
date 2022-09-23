FROM python:3.8-slim-buster

RUN apt update && apt install -y curl libpq-dev gcc

RUN curl -sSL https://install.python-poetry.org | \
    POETRY_HOME=/opt/poetry POETRY_VERSION=1.1.13 python && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

COPY ./pyproject.toml ./poetry.lock* /app/
WORKDIR /app
RUN poetry install --no-root --no-dev

COPY ./jobbergate_api /app/jobbergate_api

CMD ["uvicorn", "jobbergate_api.main:app", "--host", "0.0.0.0", "--port", "80"]
