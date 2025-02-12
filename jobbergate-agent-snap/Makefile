SHELL:=/bin/bash

.PHONY: install
install:  ## Install the dev tools

.PHONY: lint
lint: install ## Run the linter
	poetry run ruff check

.PHONY: type
type: install ## Run the type checker
	poetry run mypy

.PHONY: qa
qa: lint type ## Run all quality assurance checks

.PHONY: format
format: install ## Run the formatter
	poetry run ruff format

.PHONY: build
build: ## Build the snap
	@snapcraft $(ARGS)

.PHONY: changes
changes:
	towncrier create --dir .. --section "Agent Snap"

.PHONY: sync-version
sync-version:
	@new_version=$$(poetry version -s --directory ../jobbergate-agent) && \
	perl -pi -e "s/(- jobbergate-agent)==.*/\1==$${new_version}/" snap/snapcraft.yaml && \
	echo "Version updated to $${new_version} in snap/snapcraft.yaml"

.PHONY: clean
clean: ## Clean all files/folders created by the project
	@find . -iname '*.pyc' -delete
	@find . -iname '*.pyo' -delete
	@find . -iname '*~' -delete
	@find . -iname '*.swp' -delete
	@find . -iname '__pycache__' -delete
	@find . -type f -name "*.snap" -delete
	@rm -r .mypy_cache || true
	@rm -r .ruff_cache || true
	@rm -r parts || true
	@rm -r prime || true
	@rm -r stage || true
	@snapcraft clean

.PHONY: help
help: ## Display target comments in 'make help'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
