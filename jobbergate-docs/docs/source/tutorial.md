# Tutorial

This guide will walk you through using Jobbergate to submit a simulation job to a Slurm cluster. During this guide, you
will:

 - Log in to the Jobbergate system
 - Upload an Application to Jobbergate
 - Render a Job Script from the Application template
 - Submit a Job Script to the cluster
 - Check the results and statuses of submitted jobs
 - Delete the resources
 - Log out of the Jobbergate system


## Setup

Follow these few steps to set up your computer to run this tutorial locally. You will need administrator privileges
on your machine to do so.


### docker-compose

For this tutorial, we will be using an instance of Jobbergate that is deployed locally using docker-compose. If you
do not have it already, follow [this guide](https://docs.docker.com/compose/install/) to install docker-compose before
you begin the tutorial.


### hostfile

You will also need to have this line added to your computer's hostfile:

```
127.0.0.1 keycloak.local
```

For Linux and OSX, this file is located at `/etc/hosts`. You will need to use sudo to update this file.

For Windows, it is found at `c:\windows\system32\drivers\etc\hosts`. You will need to use administrator rights to
update this file.


### Clone Jobbergate with git

You will also need to clone the Jobbergate source code to your machine. Use this command to clone the repo from GitHub:

```shell
$ git clone git@github.com:omnivector-solutions/jobbergate.git
```

Then, change to the directory `jobbergate-composed` directory where Jobbergate was cloned:

```shell
$ cd jobbergate/jobbergate-composed
```


### Start the Jobbergate Services

Next, you will need to spin up the Jobbergate services. We will do this with docker-compose using the following command:

```shell
$ docker-compose up --build
```


This will take a little time to spin up all the services. To check if everything is operating as expected, you may
use this command:

```shell
docker-compose ps
```

If everything is operating as it should, you will see output that looks like this:

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
slurmrestd                                  "/usr/local/bin/slur…"   slurmrestd            running             0.0.0.0:6820->6820/tcpOnce everything is
```

The `STATUS` for each service should be "running" except for the `minio-create-bucket` and `jobbergate-cli`
containers which should be "exited"

Now, you can connect to the `jobbergate-cli` container to begin issuing commands:

```shell
$ docker-compose run jobbergate-cli bash
```

You should now see a new command prompt line that looks something like this::

```shell
root@e226a9a401d1:/app#
```

Test that you are able to issue Jobbergate commands by listing the avaiable commands like so:

```shell
jobbergate --help
```

This should show a usage description of the app and the avaialble sub-commands


## Log in to Jobbergate

Before you can interact with Jobbergate data, you will need to log into the system. In the tutorial used in this
example, only a single user exists. This guide will exclusively use this user, however, you can create more by logging
into the Keycloak server (Described in the Appendix).

Logging in through the Jobbergate CLI is done via the command:

```shell
$ jobbergate login

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

You are now logged in through the CLI. Your auth token will be cached automatically for you, so you should not need to
log in again for some time. However, your session will expire. If your token is no longer valid, the CLI will notify
you. At that point, you should go through the login process again.


**TODO**: Update for Job Scripts
## Upload an Application to Jobbergate

The first step in running a simulation job through Jobbergate is to create an Application for it. An application is a
reusable template that describes both the Job Script template as well as the template variables whose values must be
supplied to create a submittable Job Script.

For this example, we will use the
[motorbike-application](https://github.com/omnivector-solutions/jobbergate/tree/main/examples/motorbike-application)
that is included with the Jobbergate git repository. For the purposes of the tutorial, the application files have
already been placed into the `jobbergate-cli` container where we are running the tutorial. To see the files that the
application is composed of, you can inspect the `/motorbike-example` folder in the running `jobbergate-cli` container.

Creating the applicaiton requires only a name and a path to the Application files. We will also give it a unique
`identifier` which will make it easer to locate later.

Issue the following Jobbergate command:

```shell
jobbergate applications create --name=tutorial --identifier=tutorial --application-path=/motorbike-example

                 Created Application
┏━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Key                     ┃ Value                       ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ id                      │ 1                           │
│ application_name        │ tutorial                    │
│ application_identifier  │ tutorial                    │
│ application_description │                             │
│ application_owner_email │ local-user@jobbergate.local │
│ application_uploaded    │ True                        │
└─────────────────────────┴─────────────────────────────┘
```

As you can see, the Application was successfully created and the Application files were uploaded as well. Now, this
Application can be used any number of times to produce Job Scripts from its template.


## Render a Job Script from the Application template

The primary purpose of the Application is to produce Job Scripts with different values substituted in for the template
variables. Thus, rendering a Job Script from an Application is fundamental to the Jobbergate workflow.

We will run the Motorbike Application to demonstate the proces.

Begin by creating a Job Script from an Application using the follow command:

```shell
$ jobbergate job-scripts create --name=tutorial --application-id=1
[?] Choose a partition: compute
[?] Choose number of nodes for job: 2
[?] Choose number of tasks per node for job: 6

                                              Created Job Script
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Key                    ┃ Value                                                                                    ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ id                     │ 1                                                                                        │
│ application_id         │ 1                                                                                        │
│ job_script_name        │ tutorial                                                                                 │
│ job_script_description │ None                                                                                     │
│ job_script_owner_email │ local-user@jobbergate.local                                                              │
└────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────┘
```

You will be prompted to enter values for:

 - The name of the partition
 - The number of compute nodes to use for the job
 - The number of tasks to use for each job on the node the job

For the tutorial, you should just use the defaults.

The command will render the templates into a Job Script that can be submitted to a Slurm cluster.

To view the rendered files, you can use the `show-files` subcommand:

```shell
$ jobbergate job-scripts show-files --id=1

╭────────────────────────────────────────────── job-script-template.py ─────────────────────────────────────────────╮
│                                                                                                                   │
│   #!/bin/bash                                                                                                     │
│   #SBATCH --partition compute                                                                                     │
│   #SBATCH --nodes=2                                                                                               │
│   #SBATCH --ntasks=6                                                                                              │
│   #SBATCH -J motorbike                                                                                            │
│   #SBATCH --output=/nfs/R-%x.%j.out                                                                               │
│   #SBATCH --error=/nfs/R-%x.%j.err                                                                                │
│   #SBATCH -t 1:00:00                                                                                              │
│                                                                                                                   │
│   # clone OpenFOAM-10 if it is not available yet                                                                  │
│   OPENFOAM_DIR=/nfs/OpenFOAM-10                                                                                   │
│   if [[ ! -d $OPENFOAM_DIR ]]                                                                                     │
│   then                                                                                                            │
│       echo "Cloning OpenFOAM-10"                                                                                  │
│       cd /nfs                                                                                                     │
│       git clone https://github.com/OpenFOAM/OpenFOAM-10.git                                                       │
│   else                                                                                                            │
│       echo "Skipping clone process...we already have the OpenFOAM-10 source code"                                 │
│   fi                                                                                                              │
│                                                                                                                   │
│   # create a working folder inside the shared directory                                                           │
│   WORK_DIR=/nfs/$SLURM_JOB_NAME-Job-$SLURM_JOB_ID                                                                 │
│   mkdir -p $WORK_DIR                                                                                              │
│   cd $WORK_DIR                                                                                                    │
│                                                                                                                   │
│   # path to the openfoam singularity image                                                                        │
│   export SINGULARITY_IMAGE=/nfs/openfoam10.sif                                                                    │
│                                                                                                                   │
│   # download the openfoam v10 singularity image if it is not available yet                                        │
│   if [[ ! -f $SINGULARITY_IMAGE ]]                                                                                │
│   then                                                                                                            │
│       echo "Fetching the singularity image for OpenFOAM-10"                                                       │
│       curl -o $SINGULARITY_IMAGE --location "https://omnivector-public-assets.s3.us-west-2.amazonaws.com/singul...│
│   else                                                                                                            │
│       echo "Skipping the image fetch process...we already have the singularity image"                             │
│   fi                                                                                                              │
│                                                                                                                   │
│                                                                                                                   │
│   # copy motorBike folder                                                                                         │
│   cp -r $OPENFOAM_DIR/tutorials/incompressible/simpleFoam/motorBike .                                             │
│                                                                                                                   │
│   # enter motorBike folder                                                                                        │
│   cd motorBike                                                                                                    │
│                                                                                                                   │
│   # clear any previous execution                                                                                  │
│   singularity exec --bind $PWD:$HOME $SINGULARITY_IMAGE ./Allclean                                                │
│                                                                                                                   │
│   # copy motorBike geometry obj                                                                                   │
│   cp $OPENFOAM_DIR/tutorials/resources/geometry/motorBike.obj.gz constant/geometry/                               │
│                                                                                                                   │
│   # define surface features inside the block mesh                                                                 │
│   singularity exec --bind $PWD:$HOME $SINGULARITY_IMAGE surfaceFeatures                                           │
│                                                                                                                   │
│   # generate the first mesh                                                                                       │
│   # mesh the environment (block around the model)                                                                 │
│   singularity exec --bind $PWD:$HOME $SINGULARITY_IMAGE blockMesh                                                 │
│                                                                                                                   │
│   # decomposition of mesh and initial field data                                                                  │
│   # according to the parameters in decomposeParDict located in the system                                         │
│   # create 6 domains by default                                                                                   │
│   singularity exec --bind $PWD:$HOME $SINGULARITY_IMAGE decomposePar -copyZero                                    │
│                                                                                                                   │
│   # mesh the motorcicle                                                                                           │
│   # overwrite the new mesh files that are generated                                                               │
│   srun singularity exec --bind $PWD:$HOME $SINGULARITY_IMAGE snappyHexMesh -overwrite -parallel                   │
│                                                                                                                   │
│   # write field and boundary condition info for each patch                                                        │
│   srun singularity exec --bind $PWD:$HOME $SINGULARITY_IMAGE patchSummary -parallel                               │
│                                                                                                                   │
│   # potential flow solver                                                                                         │
│   # solves the velocity potential to calculate the volumetric face-flux field                                     │
│   srun singularity exec --bind $PWD:$HOME $SINGULARITY_IMAGE potentialFoam -parallel                              │
│                                                                                                                   │
│   # steady-state solver for incompressible turbutent flows                                                        │
│   srun singularity exec --bind $PWD:$HOME $SINGULARITY_IMAGE simpleFoam -parallel                                 │
│                                                                                                                   │
│   # after a case has been run in parallel                                                                         │
│   # it can be reconstructed for post-processing                                                                   │
│   singularity exec --bind $PWD:$HOME $SINGULARITY_IMAGE reconstructParMesh -constant                              │
│   singularity exec --bind $PWD:$HOME $SINGULARITY_IMAGE reconstructPar -latestTime                                │
│                                                                                                                   │
╰────────────────────────────────────── This is the main job script file ───────────────────────────────────────────╯
```

Notice that the values that we supplied for the questions asked by the applicaiton have been rendered into the resulting
Job Script:

```
#SBATCH --partition compute
#SBATCH --nodes=2
#SBATCH --ntasks=6
```


## Submit a Job Script to the cluster

Now that we have produced a Job Script from the source Applicaiton, we can now submit this to the Slurm cluster. In this
tutorial, we have one attached cluster named `local-slurm`. We will use this name when we are submitting the Job
Script to make sure it runs on the correct cluster.

Create the Job Submission from the Job Script with the following command:

```shell
jobbergate job-submissions create --name=tutorial --job-script-id=1 --cluster-name=local-slurm

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


## Check the results and statuses of submitted jobs

We can look up the status of a Job Submission using the following command:

```shell
jobbergate job-submissions get-one --id=1

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

Notice that the status of the Job Submission has now changed to "SUBMITTED". This means that the Jobbergate Agent has
pulled the Job Script down and submitted it to the cluster named `local-slurm`. The status will remain the same until
the Job Script finishes executing. The Jobbergate Agent will watch for the job to finish in Slurm, and will update the
status of the Job Submission to "COMPLETE".

In this tutorial, we have locally mounted a "fake" NFS folder to contain the output from the job running in slurm. You
can watch the output as Slurm processes the job by tailing the terminal output file that Slurm produces and displaying
30 lines at a time (this output is truncated to 30 lines):

```shell
$ tail -n 30 /nfs/R-motorbike.1.out

Cloning OpenFOAM-10
Cloning into 'OpenFOAM-10'...
Fetching the singularity image for OpenFOAM-10
Cleaning /home/local-user case
/*---------------------------------------------------------------------------*\
  =========                 |
  \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\    /   O peration     | Website:  https://openfoam.org
    \\  /    A nd           | Version:  10
     \\/     M anipulation  |
\*---------------------------------------------------------------------------*/
Build  : 10
Exec   : /opt/OpenFOAM/OpenFOAM-10/platforms/linux64GccDPInt32Opt/bin/surfaceFeatures
Date   : Sep 29 2022
Time   : 19:40:12
Host   : "c1"
PID    : 329
I/O    : uncollated
Case   : /home/local-user
nProcs : 1
sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE).
fileModificationChecking : Monitoring run-time modified files using timeStampMaster (fileModificationSkew 10)
allowSystemOperations : Allowing user-supplied system call operations

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
Create time

Reading "surfaceFeaturesDict"
```


This command will continue to collect output until you quit with `Ctrl-C`. It will take some time to even begin seeing
output here as the job downloads OpenFOAM resources to run the job. Subsequent runs will take advantage of local caching
and complete *much* more quickly. So, please be patient!


```shell
$ jobbergate job-submissions get-one --id=1

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
│ status                     │ COMPLETED                   │
└────────────────────────────┴─────────────────────────────┘
```

Don't worry if the Job Submission seems to be stuck and does not change for a while. If it fails, the status
of the Job Submission will change to "FAILED". If you don't see this, the Job Submission is still being processed.

In this tutorial, the results from the Job Submission are available in the `/nfs` directory. All of the processing
files can be found there:

```shell

$ ls /nfs/motorbike-Job-1/motorbike/

0  500  Allclean  Allrun  constant  postProcessing  processor0  processor1  processor2  processor3  processor4  processor5  system
```


## Delete the resources

Sometimes it is useful to remove resources that have been created in Jobbergate.

When deleting the resources, you must delete in reverse order of creation:

```
Job Submission -> Job Script -> Application
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


Then finally delete the Application:

```shell
$ jobbergate applications delete --id=1

╭───────────────────────────────────────── Application delete succeeded ────────────────────────────────────────────╮
│                                                                                                                   │
│   The application was successfully deleted.                                                                       │
│                                                                                                                   │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

If you attempt to delete a resource before any that were created _from_ it, you will see an error like this:

```shell
$ jobbergate applications delete --id=1

╭─────────────────────────────────────────────── REQUEST FAILED ────────────────────────────────────────────────────╮
│ Request to delete application was not accepted by the API:                                                        │
│ There are job_scripts that reference id 1.                                                                        │
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
