#!/bin/bash

# Copied from: https://pythonspeed.com/articles/build-secrets-docker-compose/
#
# Provisional method for securely adding pypi password during build

set -euo pipefail
if [ -f /run/secrets/pypi_password ]; then
       export PYPI_PASSWORD=$(cat /run/secrets/pypi_password)
fi
