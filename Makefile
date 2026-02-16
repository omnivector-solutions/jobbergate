SHELL:= /bin/bash

qa:
	$(MAKE) -C jobbergate-agent qa
	$(MAKE) -C jobbergate-api qa
	$(MAKE) -C jobbergate-cli qa
	$(MAKE) -C jobbergate-core qa
	$(MAKE) -C jobbergate-agent-snap qa

format:
	$(MAKE) -C jobbergate-agent format
	$(MAKE) -C jobbergate-api format
	$(MAKE) -C jobbergate-cli format
	$(MAKE) -C jobbergate-core format
	$(MAKE) -C jobbergate-agent-snap format

clean:
	$(MAKE) -C jobbergate-agent clean
	$(MAKE) -C jobbergate-api clean
	$(MAKE) -C jobbergate-cli clean
	$(MAKE) -C jobbergate-core clean
	$(MAKE) -C jobbergate-agent-snap clean

.PHONY: changes
changes:
	uv run towncrier create --dir .

.PHONY: changelog-draft
changelog-draft:
	uv run towncrier build --draft --version $$(cd jobbergate-core && uv tool run hatch version)

.PHONY: changelog-build
changelog-build:
	uv run towncrier build --yes --version $$(cd jobbergate-core && uv tool run hatch version)
