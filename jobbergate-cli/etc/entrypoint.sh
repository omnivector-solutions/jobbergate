#!/bin/bash

set -e
cd /app
poetry install --without=dev

# Start a bash shell
exec /bin/bash