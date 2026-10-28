ARG PG_MAJOR=17
FROM ghcr.io/cloudnative-pg/postgresql:${PG_MAJOR}-bookworm

ARG PG_MAJOR=17

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
    && curl -fsSL --proto '=https' --tlsv1.2 https://packagecloud.io/timescale/timescaledb/gpgkey \
        | gpg --dearmor -o /usr/share/keyrings/timescaledb.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/timescaledb.gpg] https://packagecloud.io/timescale/timescaledb/debian/ $(. /etc/os-release && echo "$VERSION_CODENAME") main" \
        > /etc/apt/sources.list.d/timescaledb.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        "timescaledb-2-postgresql-${PG_MAJOR}" \
    && apt-get purge -y --auto-remove curl gnupg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /etc/apt/sources.list.d/timescaledb.list /usr/share/keyrings/timescaledb.gpg

USER 26
