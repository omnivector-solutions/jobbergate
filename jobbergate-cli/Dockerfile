FROM python:3.10-slim-buster

WORKDIR /app

RUN apt update && apt install -y curl libpq-dev gcc

RUN curl -sSL  https://install.python-poetry.org | \
    POETRY_HOME=/opt/poetry POETRY_VERSION=1.5.1 python && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

COPY ./pyproject.toml ./poetry.lock* ./README* ./LICENSE* /app/
COPY ./jobbergate_cli /app/jobbergate_cli
RUN poetry install --without=dev
