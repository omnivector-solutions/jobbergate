FROM python:3.14-slim-bookworm AS builder

WORKDIR /app

RUN apt update && apt --no-install-recommends install -y git && apt-get clean

COPY --from=ghcr.io/astral-sh/uv:0.10.8@sha256:88234bc9e09c2b2f6d176a3daf411419eb0370d450a08129257410de9cfafd2a /uv /usr/local/bin/uv

# Keep full repository in builder so hatch-vcs sees a clean tracked worktree.
COPY . .

RUN uv sync --frozen --no-editable --no-python-downloads --package jobbergate-cli --no-dev

FROM python:3.14-slim-bookworm AS runner

WORKDIR /app

RUN groupadd --system appuser \
    && useradd --system --create-home --gid appuser appuser

# Copy files before switching user
COPY --from=builder /app/.venv .venv
COPY --from=builder /app/jobbergate-cli/README.md README.md
COPY --from=builder /app/jobbergate-cli/LICENSE LICENSE

# Change ownership of /app to the new user and switch to it
RUN chown -R appuser:appuser /app

WORKDIR /workspace
RUN chown -R appuser:appuser /workspace

USER appuser

ENTRYPOINT ["/app/.venv/bin/jobbergate"]
