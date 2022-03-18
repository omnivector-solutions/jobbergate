#!/bin/bash

poetry run dev-tools db upgrade
poetry run dev-tools dev-server --port=8000

tail -f /dev/null
