#!/bin/bash

set -e

echo "---> Starting the MUNGE Authentication service (munged) ..."
service munge start

echo "---> Waiting for slurmctld to become active before starting slurmd..."

until 2>/dev/null >/dev/tcp/slurmctld/6817
do
    echo "-- slurmctld is not available.  Sleeping ..."
    sleep 2
done
echo "-- slurmctld is now active ..."

echo "---> Starting the Slurm Node Daemon (slurmd) ..."
/usr/sbin/slurmd -Dvvv

echo "---> Starting Jobbergate-agent ..."
cd /app
poetry install
poetry run jg-run