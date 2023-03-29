FROM python:3.8-slim-buster AS builder

WORKDIR /app

RUN apt update && apt install -y curl libpq-dev gcc make

RUN curl -sSL  https://install.python-poetry.org | \
    POETRY_HOME=/opt/poetry POETRY_VERSION=1.1.13 python && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

ADD jobbergate-docs /app/jobbergate-docs
ADD jobbergate-core /app/jobbergate-core

WORKDIR /app/jobbergate-docs

RUN make docs

FROM python:3.8-slim-buster AS final

COPY --from=builder /app/jobbergate-docs/build /app/build

CMD ["sh", "-c", "python -m http.server --bind 0.0.0.0 --directory /app/build 8887"]