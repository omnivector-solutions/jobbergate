SHELL:=/bin/bash

.PHONY: lint
lint: ## Run the linters
	tox -e lint

.PHONY: type
type: ## Run the type checker
	tox -e type

.PHONY: qa
qa: lint type ## Run all quality assurance checks

.PHONY: format
format: ## Run the formatter
	tox -e format

.PHONY: build
build: clean ## Build the snap
	@snapcraft -v
	mv *.snap jobbergate-agent.snap

.PHONY: changes
changes: ## Create a new change entry for the changelog
	towncrier create --dir .. --section "Agent Snap"

.PHONY: sync-version
sync-version: ## Synchronize the agent version into snapcrat.yaml
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
	@find . -iname '.zip' -delete
	@find . -type f -name "*.snap" -delete
	@find . -iname 'commit-sha.txt' -delete
	@rm -rf .mypy_cache
	@rm -rf .ruff_cache
	@rm -rf .tox
	@rm -rf .venv
	@rm -rf parts
	@rm -rf prime
	@rm -rf stage
	@snapcraft clean

.PHONY: help
help: ## Display target comments in 'make help'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
