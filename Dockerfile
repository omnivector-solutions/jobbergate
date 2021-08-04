FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8-slim

RUN apt-get -y update
RUN apt-get install -y --fix-missing build-essential cmake libpq-dev curl

RUN pip install 'poetry==1.1.7'
RUN poetry config virtualenvs.create false --local

ENV MODULE_NAME="jobbergateapi2.main"

RUN mkdir app
WORKDIR app

COPY ./pyproject.toml /app/
COPY ./poetry.lock /app/

RUN poetry install

COPY ./jobbergateapi2 /app/jobbergateapi2/
