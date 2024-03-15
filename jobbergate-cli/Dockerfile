FROM python:3.10-slim-buster

WORKDIR /app

RUN apt update && apt install -y curl libpq-dev gcc

RUN curl -sSL  https://install.python-poetry.org | \
    POETRY_HOME=/opt/poetry POETRY_VERSION=1.5.1 python && \
    ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry && \
    poetry config virtualenvs.create false

COPY ./pyproject.toml ./poetry.lock* ./README* ./LICENSE* /app/
COPY ./etc/entrypoint.sh /app/entrypoint.sh
WORKDIR /app

VOLUME /app/jobbergate_cli
VOLUME /jobbergate-core

ENTRYPOINT /app/entrypoint.sh
