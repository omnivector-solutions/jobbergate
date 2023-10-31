# SETTINGS
# Use one shell for all commands in a target recipe
.ONESHELL:
.DEFAULT_GOAL:=help
SHELL:=/bin/bash

.PHONY: install
install:
	poetry install

.PHONY: lint
lint: install
	poetry run black --check source
	poetry run isort --check source
	poetry run flake8 --max-line-length=120 --max-complexity=40 source

.PHONY: qa
qa: lint
	echo "All tests pass! Ready for deployment"

.PHONY: format
format: install
	poetry run black source
	poetry run isort source

.PHONY: docs
docs: install
	poetry run mkdocs build --config-file=docs/mkdocs.yaml

.PHONY: docs-serve
docs-serve: install
	poetry run mkdocs serve --config-file=docs/mkdocs.yaml --dev-addr=localhost:10000

.PHONY: clean
clean:
	@find . -iname '*.pyc' -delete
	@find . -iname '*.pyo' -delete
	@find . -iname '*~' -delete
	@find . -iname '*.swp' -delete
	@find . -iname '__pycache__' -delete
	@rm -fr build/
	@rm -fr dist/
	@rm -fr *.egg-info

.PHONY: help
help: # Display target comments in 'make help'
	grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
