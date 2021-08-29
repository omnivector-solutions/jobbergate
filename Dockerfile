FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8-slim

RUN apt-get -y update
RUN apt-get install -y --fix-missing build-essential cmake libpq-dev curl

RUN pip install 'poetry==1.1.7'

ENV MODULE_NAME="jobbergateapi2.main"

RUN mkdir app
WORKDIR app

COPY ./pyproject.toml /app/
COPY ./poetry.lock /app/

COPY hack_build_secrets.sh .
RUN --mount=type=secret,id=pypi_password ./hack_build_secrets.sh
ENV POETRY_HTTP_BASIC_PYPICLOUD_USERNAME=admin
ENV POETRY_HTTP_BASIC_PYPICLOUD_PASSWORD=$PYPI_PASSWORD

RUN poetry config virtualenvs.create false --local
RUN poetry install

COPY ./jobbergateapi2 /app/jobbergateapi2/
