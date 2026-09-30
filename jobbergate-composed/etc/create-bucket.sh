#!/bin/sh
set -e

if ! /garage bucket info test-jobbergate-resources >/dev/null 2>&1; then
	/garage bucket create test-jobbergate-resources
fi
/garage bucket allow --read --write --owner test-jobbergate-resources --key GK0123456789abcdef0123456789abcdef
