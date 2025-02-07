.ONESHELL:
.DEFAULT_GOAL:=help
SHELL:=/bin/bash
PACKAGE_NAME:=jobbergate_api

install:  ## Install the package locally for development.
	poetry install

test: install  ## Run the unit tests.
	poetry run pytest

mypy: install  ## Run static type checking on the code base.
	poetry run mypy ${PACKAGE_NAME} --pretty

lint: install  ## Run linters over the code base.
	poetry run ruff check tests ${PACKAGE_NAME}

format: install  ## Autoformat the code base.
	poetry run ruff format tests ${PACKAGE_NAME}

qa: test mypy lint format  ## Run all quality checks.
	echo "All quality checks pass!"

local: install  ## Run a local dev server.
	poetry run dev-tools dev-server --port=8000

# To include a message with the generated migration, set the MESSAGE variable in the make command:
#   $ make db-migration MESSAGE="this migration applies foo to bar"
db-migrate: install  ## Create a migration for the database based on the current models.
	poetry run alembic --config=alembic/alembic.ini revision --autogenerate --message "$(MESSAGE)"

# To override the upgrade target from head, set the UPGRADE_TARGET variable in the make command:
#   $ make db-upgrade UPGRADE_TARGET=bf1e9e
UPGRADE_TARGET ?= head
db-upgrade: install  ## Upgrade the database to a specified target. Defaults to latest.
	poetry run alembic --config=alembic/alembic.ini upgrade $(UPGRADE_TARGET)

.PHONY: changes
changes:
	towncrier create --dir .. --section API

clean:  ## Clean up build artifacts and other junk
	@find . -iname '*.pyc' -delete
	@find . -iname '*.pyo' -delete
	@find . -iname '*~' -delete
	@find . -iname '*.swp' -delete
	@find . -iname '__pycache__' -delete
	@find . -name '*.egg' -print0|xargs -0 rm -rf --
	@rm -rf .eggs/
	@rm -fr build/
	@rm -fr dist/
	@rm -fr *.egg-info

# Recipe stolen from: https://gist.github.com/prwhite/8168133?permalink_comment_id=4160123#gistcomment-4160123
help:  ## Show help message
	@awk 'BEGIN {FS = ": .*##"; printf "\nUsage:\n  make \033[36m\033[0m\n"} /^[$$()% 0-9a-zA-Z_-]+(\\:[$$()% 0-9a-zA-Z_-]+)*:.*?##/ { gsub(/\\:/,":", $$1); printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
