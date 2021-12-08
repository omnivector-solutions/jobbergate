FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8-slim

RUN apt-get -y update
RUN apt-get install -y --fix-missing build-essential cmake libpq-dev curl

RUN pip install 'poetry==1.1.7'

ENV MODULE_NAME="jobbergate_api.main"

RUN mkdir app
WORKDIR app

COPY ./pyproject.toml /app/
COPY ./poetry.lock /app/

RUN poetry config virtualenvs.create false --local
RUN poetry install

COPY ./jobbergate_api /app/jobbergate_api/
