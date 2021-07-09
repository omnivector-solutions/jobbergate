FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8-slim

RUN apt-get -y update
RUN apt-get install -y --fix-missing build-essential cmake libpq-dev

ENV MODULE_NAME="jobbergateapi2.main"
COPY . /app
RUN pip install .
