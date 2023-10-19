# Tutorial

Welcome to this step-by-step tutorial that introduces the basic functionalities of Jobbergate!
to seamlessly upload a Job Script and submit it to a Slurm cluster using the Jobbergate CLI.

In this walk-through, you will learn how to upload a Job Script and submit it to a Slurm cluster using the
Jobbergate CLI. To accomplish this, we will guide you through the following steps:

 - Initiating a session by logging into the Jobbergate system
 - Uploading a basic Job Script to Jobbergate
 - Submitting the Job Script to the cluster
 - Reviewing the results and monitoring the status of your submitted job
 - Cleaning up by deleting the Job Script
 - Logging out of the Jobbergate system


## Getting Started

Before diving into the tutorial, there are some initial setup steps that are needed to ensure that your computer is
prepared to run the tutorial locally. Make sure you have administrative access to your machine, as it's required for
the setup process.


### Install docker-compose

For this tutorial, we will be using an instance of Jobbergate that is deployed locally along-side a local Slurm cluster.
We will set all this up using docker-compose. If you do not have it already, follow
[this guide](https://docs.docker.com/compose/install/) to install docker-compose before you continue the tutorial.


### Update the hostfile

Next, you’ll need to add the following line to your computer’s hostfile:

```
127.0.0.1 keycloak.local
```

#### For Linux and OSX users:

 - The hostfile is located at `/etc/hosts`.
 - Open a terminal.
 - Use this command to open the file in a text editor
   ```shell
   sudo nano /etc/hosts
   ```
   (you may, of course, substitute your editor of choice here)
 - Add the above line at the end of the file.
 - Save and close the file.


#### For Windows users:

 - The hostfile can be found at c:\windows\system32\drivers\etc\hosts.
 - Open Notepad as an administrator.
 - Open the hostfile in Notepad.
 - Append the above line to the file.
 - Save and exit.



### Clone Jobbergate with git

To run the Jobbergate and Slurm locally, you will first need a copy of the Jobbergate source code. The easiest way to
get it is to use Git to download the source code repository from GitHub onto your machine.

Git is a version control system that lets you manage and keep track ofyour source code history. If you haven't installed
it yet, download and install Git using the instructions available [here](https://git-scm.com/).

With Git installed, you can now clone the Jobbergate source code from its GitHub repository. Cloning allows you to have
a local copy (or clone) of the source code on your machine.

Run the following command in your terminal:

```shell
$ git clone git@github.com:omnivector-solutions/jobbergate.git
```

Now you have a full copy of the Jobbergate source code including the Docker Compose configuration to stand up a local
Slurm Cluster and the example Job Script we will be using for this tutorial.

Next, switch to the directory in the source code that contains the Docker Compose configuration:

```shell
$ cd jobbergate/jobbergate-composed
```


### Start the Jobbergate Services

With the Jobbergate source code in place, it's time to initiate the Jobbergate Services and the local Slurm cluster
using Docker Compose. Follow the steps outlined below to get things up and running.

#### Start up the services
Run the following command to build and start the services. The `--build` flag ensures that Docker Compose build the
images before attempting to start the services. The `--detach` flag runs the services in the background so that you
can run other commands in the terminal.

```shell
$ docker-compose up --build --detach
```

This operation might take a few minutes as it involves building the images and starting up all the associated services.


#### Verify the status of the services

To confirm that all the services are running smoothly, execute the following command. It will list the status of all the
services initiated by Docker Compose:

```shell
docker-compose ps
```

If the services are up and running as expected, you should see output similar to the following, indicating that all the
services are in a healthy state

```
NAME                                        COMMAND                  SERVICE               STATUS              PORTS
c1                                          "/usr/local/bin/slur…"   c1                    running             6818/tcp
c2                                          "/usr/local/bin/slur…"   c2                    running             6818/tcp
jobbergate-composed-cluster-agent-1         "/agent/entrypoint.sh"   cluster-agent         running
jobbergate-composed-db-1                    "docker-entrypoint.s…"   db                    running             0.0.0.0:5432->5432/tcp
jobbergate-composed-jobbergate-api-1        "/bin/sh -c /app/dev…"   jobbergate-api        running (healthy)   0.0.0.0:8000->80/tcp
jobbergate-composed-jobbergate-cli-1        "python3"                jobbergate-cli        exited (0)
jobbergate-composed-keycloak.local-1        "/opt/keycloak/bin/k…"   keycloak.local        running             0.0.0.0:8080->8080/tcp, 8443/tcp
jobbergate-composed-minio-1                 "/usr/bin/docker-ent…"   minio                 running             0.0.0.0:9000-9001->9000-9001/tcp
jobbergate-composed-minio-create-bucket-1   "/create-bucket.sh"      minio-create-bucket   exited (1)
mysql                                       "docker-entrypoint.s…"   mysql                 running             3306/tcp, 33060/tcp
slurmctld                                   "/usr/local/bin/slur…"   slurmctld             running             6817/tcp
slurmdbd                                    "/usr/local/bin/slur…"   slurmdbd              running             6819/tcp
slurmrestd                                  "/usr/local/bin/slur…"   slurmrestd            running             0.0.0.0:6820->6820/tcp
```

The `STATUS` for each service should be "running" except for the `minio-create-bucket` and `jobbergate-cli`
services which should be "exited".


#### Confirm Jobbergate CLI availability

Since this tutorial relies on running commands in the Jobbergate CLI, it's essential to verify that the CLI is available
and working as expected at this juncture.


First, initiate a connection to the `jobbergate-cli` container by executing the following command. This gives you
direct access to the CLI.

```shell
$ docker-compose run jobbergate-cli bash
```

Upon successful connection, your command prompt should change to reflect that you're inside the container. It will look
something like this:

```shell
root@e226a9a401d1:/app#
```

This confirms that you're now operating within the `jobbergate-cli` container environment.

Next, we need to make sure that the Jobbergate CLI is available and accepting commands. Test this by listing the
available commands in Jobbergate CLI with the `--help` option:

```shell
jobbergate --help
```

The command above will yield a detailed description of the CLI's usage and the variety of sub-commands it provides:

```
 Usage: jobbergate [OPTIONS] COMMAND [ARGS]...

 Welcome to the Jobbergate CLI!
 More information can be shown for each command listed below by running it with the --help option.

╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --verbose               --no-verbose                                     Enable verbose logging to the terminal      │
│                                                                          [default: no-verbose]                       │
│ --full                  --no-full                                        Print all fields from CRUD commands         │
│                                                                          [default: no-full]                          │
│ --raw                   --no-raw                                         Print output from CRUD commands as raw json │
│                                                                          [default: no-raw]                           │
│ --version               --no-version                                     Print the version of jobbergate-cli and     │
│                                                                          exit                                        │
│                                                                          [default: no-version]                       │
│ --install-completion                    [bash|zsh|fish|powershell|pwsh]  Install completion for the specified shell. │
│                                                                          [default: None]                             │
│ --show-completion                       [bash|zsh|fish|powershell|pwsh]  Show completion for the specified shell, to │
│                                                                          copy it or customize the installation.      │
│                                                                          [default: None]                             │
│ --help                                                                   Show this message and exit.                 │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ applications        Commands to interact with applications                                                           │
│ job-scripts         Commands to interact with job scripts                                                            │
│ job-submissions     Commands to interact with job submissions                                                        │
│ login               Log in to the jobbergate-cli by storing the supplied token argument in the cache.                │
│ logout              Logs out of the jobbergate-cli. Clears the saved user credentials.                               │
│ show-token          Show the token for the logged in user.                                                           │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```


## Log in to Jobbergate

To begin working with Jobbergate data, you must first sign into the system. For the purpose of this tutorial, there's
just one user available. We'll soley focus on this user in this guide, but should you wish to add more users, you can
do so by accessing the Keycloak server (details provided in the [Appendix](#appendix)).

To log in using the Jobbergate CLI, execute the following command:

```shell
$ jobbergate login
```

The CLI will provide a URL for you to log into your account:

```
╭─────────────────────────────────────────────── Waiting for login ─────────────────────────────────────────────────╮
│                                                                                                                   │
│   To complete login, please open the following link in a browser:                                                 │
│                                                                                                                   │
│     http://keycloak.local:8080/realms/jobbergate-local/device?user_code=CZAU-TZAH                                 │
│                                                                                                                   │
│   Waiting up to 5.0 minutes for you to complete the process...                                                    │
│                                                                                                                   │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Waiting for web login... ━╺━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   3% 0:04:50
```

Open the URL shown in a browser and log in as "local-user":

 - **username**: "local-user"
 - **password**: "local"

When prompted, grant all the requested access privileges to the CLI. Once you have finished, the CLI will show that you
have successfully logged in:

```shell
╭────────────────────────────────────────────────── Logged in! ─────────────────────────────────────────────────────╮
│                                                                                                                   │
│   User was logged in with email 'local-user@jobbergate.local'                                                     │
│                                                                                                                   │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

You are now logged in through the CLI! Your auth token will be cached automatically for you, so you should not need to
log in again for some time. However, be aware that your session does expire; you will have to log in again to get a new
token. If this happens, the CLI will alert you that your token is invalid. When you receive this notification, you will
need to log in anew.


## Upload a Job Script to Jobbergate

Job Scripts are integral to Jobbergate, serving as the foundation for running simulations on our cluster. To initiate a
simulation, your first task is to upload the Job Script to the Jobbergate API.

Within each Job Script, an entrypoint file is designated. This is the specific script that Slurm executes to commence
the simulation on the cluster.


### Get the example script

To keep this tutorial focused on using Jobbergate and not any of the complexities of simulations or operating a cluster,
we will use a
[very basic example](https://github.com/omnivector-solutions/jobbergate/tree/main/examples/simple-job-script.py)
job script. We will need a copy of this script where the `jobbergate-cli` can access it. Since it's a small script, we
can just copy/paste it into the container where we are accessing the `jobbergate-cli`.

In the terminal where you were typing jobbergate commands, enter this command:

```shell
cat > simple-job-script.py
```

Paste the contents of the job script and then press `ctrl-d` on your keyboard. This will create a saved copy of the
job script that's ready to submit with the `jobbergate-cli`. To ensure that the command sequence captured the intended
script contents, execute the following command to review the job script:

```shell
cat simple-job-script.python3
```

The script should appear exactly as you see it on the link above.



### Create the Job Script from the example

Now it's time to create a Job Script entry within the Jobbergate system. We'll use the `create` subcommand associated
with the `job-scripts` command. To view all the options that come with this sub-command, you can use the `--help`
option:

```shell
jobbergate job-scripts create --help
```

Now, let's create the Job Script. In your terminal, type:

```shell
jobbergate job-scripts create --name=tutorial --job-script-path=simple-job-script.py
```

You should see output like this indicating that the Job Script was successfully created:

```
                 Created Job Script
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Key            ┃ Value                            ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ id             │ 1                                │
│ application_id │ None                             │
│ name           │ tutorial                         │
│ description    │                                  │
│ owner_email    │ local-user@jobbergate.local-mail │
└────────────────┴──────────────────────────────────┘
```

Great, your Job Script is now prepared and ready for submission to the cluster!

!!! Note

    Keep track of the `id` value produced by your command. The tutorial text assumes that it is "1", but it may be
    different if you have done the tutorial before or had to restart!

To confirm that the Job Script has been uploaded correctly, you can review the file content using the
`show-files` subcommand:

```shell
$ jobbergate job-scripts show-files --id=1
```

The file should appear exactly as it does on the link above.


## Submit a Job Script to the cluster

With the Job Script ready, the next step is to submit it to the Slurm cluster. In this tutorial, a cluster named
`local-slurm` is already attached and available for use. We will specify this cluster name when submitting the Job
Script to ensure it is executed on the appropriate cluster.


### Create the Job Submission

We will use the `create` subcommand of the `job-submissions` command to submit the job to the cluster. To see all the
options available for this command, we can use the `--help` option again:

```shell
jobbergate job-submissions create --help
```

For the tutorial, we need to issue the following command:

```shell
jobbergate job-submissions create --name=tutorial --job-script-id=1 --cluster-name=local-slurm
```

The command should produce output that looks like this:
```
                   Created Job Submission
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Key                        ┃ Value                       ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ id                         │ 1                           │
│ job_script_id              │ 1                           │
│ client_id                  │ local-slurm                 │
│ slurm_job_id               │ None                        │
│ execution_directory        │ None                        │
│ job_submission_name        │ tutorial                    │
│ job_submission_description │ None                        │
│ job_submission_owner_email │ local-user@jobbergate.local │
│ status                     │ CREATED                     │
└────────────────────────────┴─────────────────────────────┘
```

The Job Submission was successfully created! However, it has not submitted to the cluster yet. This will happen when the
Jobbergate Agent that is running remotely in the cluster pulls all "CREATED" Job Submissions down from the API and
submits them to Slurm one by one.

!!! Note

    Again, be careful to use the correct `id` produced by this command for the remainder of the tutorial!


### Check the status of the submitted job

We can look up the status of a Job Submission using the following command:

```shell
jobbergate job-submissions get-one --id=1
```

This command should produce output that looks like:

```
                       Job Submission
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Key                        ┃ Value                       ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ id                         │ 1                           │
│ job_script_id              │ 1                           │
│ client_id                  │ local-slurm                 │
│ slurm_job_id               │ 1                           │
│ execution_directory        │ None                        │
│ job_submission_name        │ tutorial                    │
│ job_submission_description │ None                        │
│ job_submission_owner_email │ local-user@jobbergate.local │
│ status                     │ SUBMITTED                   │
└────────────────────────────┴─────────────────────────────┘
```

If the `status` reported by your command is `CREATED`, don't worry! The Jobbergate Agent just hasn't retrieved and
submitted the job script yet. Wait a few more seconds and dry again. You should now see the status change to
`SUBMITTED`.

When the Job Submission status shifts to "SUBMITTED", it indicats that the Jobbergate Agent has retrieved the Job Script
and submitted it to the `local-slurm` cluster. This status will persist until the completion of the Job Script's
execution. The Jobbergate Agent continuaously monitors the job's progress within slurm, and , upon its completion, will
update the Job Submission status to "COMPLETE".


### Check the results of the job

In this tutorial, we have locally mounted a "fake" NFS folder to contain the output from the job running in slurm. When
the job finishes running, it will produce an output file in this folder. First we need to verify that the file was
produced by listing the contents of the `nfs` directory:

```shell
ls /nfs
```

If the job completed, you should see a file in the `/nfs` directory named `simple-output.txt`. Check the contents of the
file with a simple `cat` command:

```
cat /nfs/simple-output.txt
```

It should look look like:

```
Simple output from c1
```

It's possible that the output says it came from c2 if slurm ran the job on the `c2` compute node instead of `c1`.


## Delete the resources

Sometimes it is useful to remove resources that have been created in Jobbergate.

When deleting the resources, you must delete in reverse order of creation:

```
Job Submission -> Job Script
```

Start by deleting the Job Submission:

```shell
$ jobbergate job-submissions delete --id=1

╭──────────────────────────────────────── Job submission delete succeeded ──────────────────────────────────────────╮
│                                                                                                                   │
│   The job submission was successfully deleted.                                                                    │
│                                                                                                                   │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```


Then delete the Job Script:

```shell

$ jobbergate job-scripts delete --id=1

╭──────────────────────────────────────── Job script delete succeeded ──────────────────────────────────────────────╮
│                                                                                                                   │
│   The job script was successfully deleted.                                                                        │
│                                                                                                                   │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

If you attempt to delete a resource before any that were created _from_ it, you will see an error like this:

```shell
$ jobbergate job-scripts delete --id=1

╭─────────────────────────────────────────────── REQUEST FAILED ────────────────────────────────────────────────────╮
│ Request to delete job-script was not accepted by the API:                                                         │
│ There are job_submissions that reference id 1.                                                                    │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
````


## Log out of the Jobbergate system

You have completed the tutorial. Try logging out of Jobbergate now:

```shell
$ jobbergate logout

╭──────────────────────────────────────────────── Logged out ───────────────────────────────────────────────────────╮
│                                                                                                                   │
│   User was logged out.                                                                                            │
│                                                                                                                   │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

This will clear any cached tokens, and any subsequent Jobbergate commands will require you to log in again


## Appendix

### Keycloak UI

You can connect to the Keycloak UI to create additional realms, clients, and users. However, the use of Keycloak is a
rather large topic that goes outside the scope of this Tutorial.

To get started, you can connect to the Keycloak UI through a browser if the server is running as a part of the
docker-compose cluster using [this local URL](http:localhost:8080). To log in as administrator use these credentials:

 - **username**: admin
 - **password**: admin
