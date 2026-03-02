#!/bin/bash

set -e
cd /app/jobbergate-api
/app/.venv/bin/dev-tools db upgrade
/app/.venv/bin/dev-tools dev-server --port=80
