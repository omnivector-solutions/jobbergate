SHELL:= /bin/bash

qa:
	$(MAKE) -C jobbergate-api qa
	$(MAKE) -C jobbergate-cli qa

format:
	$(MAKE) -C jobbergate-api format
	$(MAKE) -C jobbergate-cli format

clean:
	$(MAKE) -C jobbergate-api clean
	$(MAKE) -C jobbergate-cli clean
