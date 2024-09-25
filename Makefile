SHELL:= /bin/bash

qa:
	$(MAKE) -C jobbergate-api qa
	$(MAKE) -C jobbergate-cli qa
	$(MAKE) -C jobbergate-agent-snap qa

format:
	$(MAKE) -C jobbergate-api format
	$(MAKE) -C jobbergate-cli format
	$(MAKE) -C jobbergate-agent-snap format

clean:
	$(MAKE) -C jobbergate-api clean
	$(MAKE) -C jobbergate-cli clean
	$(MAKE) -C jobbergate-agent-snap clean
