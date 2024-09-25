# jobbergate-agent-snap
The Jobbergate Agent bundled into a Snap.

# Installation instructions

For installing from the remote store, run:
```bash
sudo snap install jobbergate-agent
```

## Basic Usage

This snap requires a few configuration values to be set before it can be used. These values are:
- base-api-url: The URL of the Jobbergate API server where the agent will send its data. Setting/unsetting this value is more interesting when using the snap in a development environment; do not change it otherwise.

- oidc-domain: The domain of the OIDC server that the agent will use for authentication. Setting/unsetting this value is more interesting when using the snap in a development environment; do not change it otherwise.

- oidc-client-id: The client ID of the OIDC application that the agent will use for authentication.

- oidc-client-secret: The client secret of the OIDC application that the agent will use for authentication.

- task-jobs-interval-seconds: The interval in seconds at which the agent will run its internal task jobs, hence sending data to the Jobbergate API server. This is optional and defaults to 30 seconds.

- task-self-update-interval-seconds: The interval in seconds at which the agent will check for updates to itself. This is optional and defaults to 30 seconds.

- sbatch-path: The absolute path to the *sbatch* command on the host system. This is optional and defaults to /usr/bin/sbatch.

- scontrol-path: The absolute path to the *scontrol* command on the host system. This is optional and defaults to /usr/bin/scontrol.

- default-slurm-work-dir: The default working directory that the agent will use when submitting jobs to the SLURM cluster. This is optional and defaults to /tmp.

- slurm-user-mapper: The user mapper that the agent will use to map the system user name to the SLURM user name. This is optional and defaults to none.

- single-user-submitter: The system user name that the agent will use to submit jobs to the SLURM cluster on behalf of in case the *single-user-submitter* is not set. This is optional and defaults to *ubuntu*.

- write-submission-files: A boolean value (true, false) that indicates whether the agent should write submission files to disk. This is optional and defaults to false.

Any configuration can be set using the *snap* command line, e.g.:
```bash
sudo snap set jobbergate-agent oidc-client-id=foo
sudo snap set jobbergate-agent oidc-client-secret=boo
```

# Development

For development purposes, you can build the `jobbergate-agent` part prior of packing the snap. To do that, run:
```bash
snapcraft prime -v
```

Add the `--debug` flag for creating a shell in case there's any error after the build is complete.

For building the snap end-to-end, run:
```bash
snapcraft -v --debug
```

Once the command completes successfully, a `.snap` file will be created in the directory. For installing this snap, run:
```bash
sudo snap install --dangerous jobbergate-agent_<snap version>_amd64.snap
```

Once the snap is installed, it is possible to check the status of the daemon and the logs:
```bash
systemctl status snap.jobbergate-agent.daemon  # check the daemon status
sudo journalctl -u snap.jobbergate-agent.daemon --follow  # follow the agent logs
```

Sometimes is important to clean the environment for deleting cached files and dependencies. For doing that, run:
```bash
sudo snapcraft clean
```

# Publish

Every time a new tag is created, a new version of the snap will be published to the *latest/candidate* and *latest/edge* channels. The version follows the pattern `<snap version>-<git revision>`, e.g. `1.0.0-8418de0`.
