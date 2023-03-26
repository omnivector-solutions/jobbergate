FROM python:3.11-slim-buster

RUN pip install poetry==1.4.1 && \
    poetry config virtualenvs.create false

COPY ./pyproject.toml ./poetry.lock ./jobbergate_core /src/
WORKDIR /src
RUN poetry install --no-root
