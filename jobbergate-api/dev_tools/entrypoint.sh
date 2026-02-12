#!/bin/bash

set -e
cd /app/jobbergate-api
uv run --package jobbergate-api dev-tools db upgrade
uv run --package jobbergate-api dev-tools dev-server --port=80
