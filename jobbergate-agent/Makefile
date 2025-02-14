.ONESHELL:
.DEFAULT_GOAL:=help
SHELL:=/bin/bash
PACKAGE_NAME:=jobbergate_agent

.PHONY: install
install: ## Install the Python dependencies
	poetry install

.PHONY: test
test: install ## Run the suite of unit tests
	poetry run pytest

.PHONY: mypy
mypy: install ## Run static typer checks
	poetry run mypy ${PACKAGE_NAME} --pretty

.PHONY: lint
lint: install ## Run linter over the code base
	poetry run ruff check tests ${PACKAGE_NAME}

.PHONY: format
format: install ## Run formatter over the code base
	poetry run ruff format tests ${PACKAGE_NAME}

.PHONY: qa ## Run all quality checks
qa: test mypy lint format
	echo "All quality checks pass!"

.PHONY: changes
changes: ## Create a new change entry for the changelog
	towncrier create --dir .. --section Agent

.PHONY: clean
clean: ## Remove cache files and similars
	@find . -iname '*.pyc' -delete
	@find . -iname '*.pyo' -delete
	@find . -iname '*~' -delete
	@find . -iname '*.swp' -delete
	@find . -iname '__pycache__' -delete
	@rm -rf .mypy_cache
	@rm -rf .pytest_cache
	@find . -name '*.egg' -print0|xargs -0 rm -rf --
	@rm -rf .eggs/
	@rm -fr build/
	@rm -fr dist/
	@rm -fr *.egg-info

.PHONY: help
help: ## Display target comments in 'make help'
	grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
