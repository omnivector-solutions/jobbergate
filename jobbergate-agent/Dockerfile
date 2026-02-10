FROM ubuntu:resolute AS builder

WORKDIR /app

# Install build dependencies
RUN apt update && apt --no-install-recommends install -y build-essential curl gcc python3 python3-pip python3-venv pipx

RUN pipx install poetry==1.5.1
ENV PATH="/root/.local/bin:$PATH"

# Copy jobbergate-core first (needed as a dependency)
COPY ./jobbergate-core /app/jobbergate-core

# Copy agent project files
COPY ./jobbergate-agent/pyproject.toml ./jobbergate-agent/poetry.lock /app/jobbergate-agent/

WORKDIR /app/jobbergate-agent

# Update the dependency path for jobbergate-core in Docker context
RUN sed -i 's|path = "../jobbergate-core"|path = "/app/jobbergate-core"|' pyproject.toml

RUN poetry config virtualenvs.in-project true \
    && poetry self add poetry-stickywheel-plugin \
    && poetry install --no-root --only main \
    && rm -rf "$POETRY_CACHE_DIR"


FROM ubuntu:resolute AS runner

WORKDIR /app

# Install runtime dependencies (python3 needed to run the application)
RUN apt update \
    && apt --no-install-recommends install -y tini python3 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system appuser \
    && useradd --system --create-home --gid appuser appuser

# Copy virtual environment from builder
COPY --from=builder /app/jobbergate-agent/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY ./jobbergate-agent/jobbergate_agent /app/jobbergate_agent
COPY ./jobbergate-core/jobbergate_core /app/jobbergate_core

# Change ownership to appuser
RUN chown -R appuser:appuser /app
USER appuser

# Use tini as init system for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["python3", "-m", "jobbergate_agent.main"]
