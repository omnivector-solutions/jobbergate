# SETTINGS
# Use one shell for all commands in a target recipe
.ONESHELL:
.DEFAULT_GOAL:=help
SHELL:=/bin/bash
PACKAGE_NAME:=jobbergate_cli

.PHONY: install
install:
	poetry install

.PHONY: test
test: install
	poetry run pytest

.PHONY: lint
lint: install
	poetry run black --check ${PACKAGE_NAME}
	poetry run isort --check ${PACKAGE_NAME}
	poetry run flake8 --max-line-length=110 --max-complexity=40 ${PACKAGE_NAME}

.PHONY: qa
qa: test lint
	echo "All tests pass! Ready for deployment"

.PHONY: format
format: install
	poetry run black ${PACKAGE_NAME}
	poetry run isort ${PACKAGE_NAME}

.PHONY: clean
clean:
	@find . -iname '*.pyc' -delete
	@find . -iname '*.pyo' -delete
	@find . -iname '*~' -delete
	@find . -iname '*.swp' -delete
	@find . -iname '__pycache__' -delete
	@rm -r .mypy_cache
	@rm -r .pytest_cache
	@find . -name '*.egg' -print0|xargs -0 rm -rf --
	@rm -rf .eggs/
	@rm -fr build/
	@rm -fr dist/
	@rm -fr *.egg-info

.PHONY: release-%
release-%:
	scripts/release.sh $(subst release-,,$@)

.PHONY: help
help: # Display target comments in 'make help'
	grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
