#!/bin/bash

set -e
cd /app
poetry run dev-tools db upgrade
poetry run dev-tools dev-server --port=80
