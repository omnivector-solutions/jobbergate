#!/bin/bash

set -e
cd /app

poetry config virtualenvs.in-project true
poetry install --without=dev

# Start a bash shell
exec /bin/bash