#!/bin/bash
set -e


echo "---> Starting the MUNGE Authentication service (munged) ..."
# The munge key lives on a shared named volume; ownership is not preserved on
# Docker Desktop (macOS), and munged refuses to start on loose permissions
chown -R munge:munge /etc/munge
chmod 700 /etc/munge
[ -f /etc/munge/munge.key ] && chmod 400 /etc/munge/munge.key
service munge start

echo "---> Starting the D-Bus system daemon (dbus) ..."
mkdir -p /run/dbus
rm -f /run/dbus/pid
dbus-daemon --system --fork

prepare_cgroups_for_slurmd() {
    # Docker Desktop (macOS) runs containers on a unified cgroup v2 hierarchy:
    # slurmd cannot create its slurmstepd scope unless the root cgroup's
    # processes are moved aside and the controllers are delegated
    echo "---> Preparing cgroup v2 delegation for slurmd ..."
    mkdir -p /sys/fs/cgroup/init
    for p in $(cat /sys/fs/cgroup/cgroup.procs); do
        echo "$p" > /sys/fs/cgroup/init/cgroup.procs 2>/dev/null || true
    done
    echo "+cpu +cpuset +memory +io +pids" > /sys/fs/cgroup/cgroup.subtree_control
    mkdir -p "/sys/fs/cgroup/system.slice/${HOSTNAME}_slurmstepd.scope"
    echo "+cpu +cpuset +memory" > /sys/fs/cgroup/system.slice/cgroup.subtree_control
}

if [[ "$1" = "slurmdbd" ]]
then
    echo "---> Starting the Slurm Database Daemon (slurmdbd) ..."
    {
        . /etc/slurm/slurmdbd.conf
        until echo "SELECT 1" | mysql -h $StorageHost -u$StorageUser -p$StoragePass 2>&1 > /dev/null
        do
            echo "-- Waiting for database to become active ..."
            sleep 2
        done
    }
    echo "-- Database is now active ..."

    exec gosu slurm /usr/sbin/slurmdbd -Dvvv
fi

if [[ "$1" = "slurmctld" ]]
then
    echo "---> Waiting for slurmdbd to become active before starting slurmctld ..."

    until 2>/dev/null >/dev/tcp/slurmdbd/6819
    do
        echo "-- slurmdbd is not available.  Sleeping ..."
        sleep 2
    done
    echo "-- slurmdbd is now active ..."

    echo "---> Starting the Slurm Controller Daemon (slurmctld) ..."
    exec gosu slurm /usr/sbin/slurmctld -Dvvv
fi

if [[ "$1" = "slurmd" ]]
then
    echo "---> Waiting for slurmctld to become active before starting slurmd..."

    until 2>/dev/null >/dev/tcp/slurmctld/6817
    do
        echo "-- slurmctld is not available.  Sleeping ..."
        sleep 2
    done
    echo "-- slurmctld is now active ..."

    prepare_cgroups_for_slurmd

    echo "---> Starting the Slurm Node Daemon (slurmd) ..."
    /usr/sbin/slurmd -Dvvv &
    wait $!
    exit $?
fi

if [[ "$1" = "jobbergate-agent" ]]
then
    echo "---> Waiting for slurmctld to become active before starting jobbergate-agent..."

    until 2>/dev/null >/dev/tcp/slurmctld/6817
    do
        echo "-- slurmctld is not available.  Sleeping ..."
        sleep 2
    done
    echo "-- slurmctld is now active ..."

    prepare_cgroups_for_slurmd

    echo "---> Starting the Slurm Node Daemon (slurmd) ..."
    /usr/sbin/slurmd -Dvvv &

    echo "---> Starting Jobbergate-agent ..."
    cd /app
    uv run --python 3.12 --no-dev --frozen --package jobbergate-agent jg-run
fi

if [[ "$1" = "jobbergate-cluster-api" ]]
then
    echo "---> Waiting for slurmctld to become active before starting jobbergate-cluster-api..."

    until 2>/dev/null >/dev/tcp/slurmctld/6817
    do
        echo "-- slurmctld is not available.  Sleeping ..."
        sleep 2
    done
    echo "-- slurmctld is now active ..."

    echo "---> Starting Jobbergate Cluster API ..."
    cd /app
    exec uv run --python 3.12 --package jobbergate-cluster-api \
        uvicorn jobbergate_cluster_api.main:app --host 0.0.0.0 --port 8000
fi

exec "$@"
