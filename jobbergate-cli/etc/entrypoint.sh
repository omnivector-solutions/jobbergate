#!/bin/bash

set -e
cd /app

uv sync --frozen --no-dev --no-cache --package jobbergate-cli

# Start a bash shell
exec /bin/bash
