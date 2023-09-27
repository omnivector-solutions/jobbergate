#!/bin/bash

set -e
cd /app
poetry install
poetry run jg-run
