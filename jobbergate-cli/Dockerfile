FROM python:3.14-slim-bookworm

WORKDIR /app

RUN apt update && apt --no-install-recommends install -y git \
    && groupadd --system appuser \
    && useradd --system --create-home --gid appuser appuser

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy workspace configuration from root
COPY .git uv.lock pyproject.toml ./
COPY jobbergate-core ./jobbergate-core
COPY jobbergate-cli ./jobbergate-cli

# Change ownership of /app to the new user and switch to it
RUN chown -R appuser:appuser /app
USER appuser

ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app/jobbergate-cli

ENTRYPOINT ["/app/jobbergate-cli/etc/entrypoint.sh"]
