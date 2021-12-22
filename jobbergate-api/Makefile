SHELL:=/bin/bash
PACKAGE_NAME:=jobbergate_api
ROOT_DIR:=$(shell dirname $(shell pwd))

install:
	poetry install

test: install
	poetry run pytest

mypy: install
	poetry run mypy ${PACKAGE_NAME} --pretty

lint: install
	poetry run black --check ${PACKAGE_NAME}
	poetry run isort --check ${PACKAGE_NAME}
	poetry run flake8 --max-line-length=110

qa: test mypy lint
	echo "All tests pass! Ready for deployment"

format: install
	poetry run black ${PACKAGE_NAME}
	poetry run isort ${PACKAGE_NAME}

run:
	poetry run uvicorn --host 0.0.0.0 jobbergateapi2.main:app --reload

update-precommit:
	poetry run pre-commit autoupdate

# To include a message with the generated migration, set the MESSAGE variable in the make command:
#   $ make db-migration MESSAGE="this migration applies foo to bar"
db-migrate: install
	poetry run alembic --config=alembic/alembic.ini revision --autogenerate --message "$(MESSAGE)"

# To override the upgrade target from head, set the UPGRADE_TARGET variable in the make command:
#   $ make db-upgrade UPGRADE_TARGET=bf1e9e
UPGRADE_TARGET ?= head
db-upgrade: install
	poetry run alembic --config=alembic/alembic.ini upgrade $(UPGRADE_TARGET)

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
