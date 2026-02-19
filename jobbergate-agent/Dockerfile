FROM ubuntu:resolute AS builder

WORKDIR /app

RUN apt update && apt --no-install-recommends install -y git && apt-get clean

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY .git uv.lock pyproject.toml ./
COPY jobbergate-core ./jobbergate-core
COPY jobbergate-agent ./jobbergate-agent

# Install with Python in a portable location
ENV UV_PYTHON_INSTALL_DIR=/app/.python
RUN uv sync --frozen --no-editable --package jobbergate-agent --no-dev

FROM ubuntu:resolute AS runner

WORKDIR /app

RUN apt update && apt --no-install-recommends install -y tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system appuser \
    && useradd --system --create-home --gid appuser appuser

# Copy virtual environment and uv-managed Python from builder
COPY --from=builder /app/.venv .venv
COPY --from=builder /app/.python .python
COPY --from=builder /app/jobbergate-agent/README.md README.md
COPY --from=builder /app/jobbergate-agent/LICENSE LICENSE

ENV PATH="/app/.venv/bin:$PATH"

# Change ownership of /app to the new user and switch to it
RUN chown -R appuser:appuser /app
USER appuser

ENTRYPOINT ["/app/.venv/bin/jg-run"]
