.ONESHELL:
.DEFAULT_GOAL:=help
SHELL:=/bin/bash
PACKAGE_NAME:=jobbergate_api

.PHONY: install
install:
	poetry install

.PHONY: test
test: install
	poetry run pytest

.PHONY: mypy
mypy: install
	poetry run mypy ${PACKAGE_NAME} --pretty

.PHONY: lint
lint: install
	poetry run ruff check tests ${PACKAGE_NAME}

.PHONY: format
format: install
	poetry run ruff format tests ${PACKAGE_NAME}

.PHONY: qa
qa: test mypy lint format
	echo "All quality checks pass!"

.PHONY: local
local: install
	poetry run dev-tools dev-server --port=8000

# To include a message with the generated migration, set the MESSAGE variable in the make command:
#   $ make db-migration MESSAGE="this migration applies foo to bar"
.PHONY: db-migrate
db-migrate: install
	poetry run alembic --config=alembic/alembic.ini revision --autogenerate --message "$(MESSAGE)"

# To override the upgrade target from head, set the UPGRADE_TARGET variable in the make command:
#   $ make db-upgrade UPGRADE_TARGET=bf1e9e
UPGRADE_TARGET ?= head
.PHONY: db-upgrade
db-upgrade: install
	poetry run alembic --config=alembic/alembic.ini upgrade $(UPGRADE_TARGET)

.PHONY: clean
clean:
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

.PHONY: help
help: # Display target comments in 'make help'
	grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
