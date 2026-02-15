FROM ubuntu:resolute AS builder

WORKDIR /app

# Install dependencies
RUN apt update && apt --no-install-recommends install -y build-essential git

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy workspace configuration from root
COPY .git uv.lock pyproject.toml ./
COPY jobbergate-core ./jobbergate-core
COPY jobbergate-agent ./jobbergate-agent

# Install only jobbergate-agent and its dependencies with Python in venv
ENV UV_PYTHON_INSTALL_DIR=/app/.python
RUN uv sync --frozen --no-editable --package jobbergate-agent --python 3.12


FROM ubuntu:resolute AS runner

WORKDIR /app

RUN apt update \
    && apt --no-install-recommends install -y build-essential ca-certificates \
    && apt-get clean \
    && groupadd --system appuser \
    && useradd --system --create-home --gid appuser appuser

# Copy virtual environment and uv-managed Python from builder
COPY --from=builder /app/.venv .venv
COPY --from=builder /app/.python .python

# Change ownership of /app to the new user and switch to it
RUN chown -R appuser:appuser /app
USER appuser

CMD ["/app/.venv/bin/jg-run"]
