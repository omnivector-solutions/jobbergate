#!/bin/bash

set -e

echo "---> Starting the MUNGE Authentication service (munged) ..."
service munge start

echo "---> Waiting for slurmdbd to become active before starting slurmctld ..."

until 2>/dev/null >/dev/tcp/slurmdbd/6819
do
    echo "-- slurmdbd is not available.  Sleeping ..."
    sleep 2
done
echo "-- slurmdbd is now active ..."

echo "---> Starting the Slurm Controller Daemon (slurmctld) ..."
gosu slurm /usr/sbin/slurmctld -Dvvv &

echo "---> Starting Jobbergate-agent ..."
cd /app
poetry install
poetry run jg-run