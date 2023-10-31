# Integration Testing

While conducting integration testing for Jobbergate, it's critical to examine the entire
cycle of the platform, ranging from the creation of an Application to remote
Job Submission via the Jobbergate Agent.

To test most of the platforms functionality, the `docker-compose` setup located in the
[Jobbergate Composed](https://github.com/omnivector-solutions/jobbergate/jobbergate-composed)
sub-project is sufficient. Begin by referring to the guide in that sub-project's README.
Pay close attention to the execution of Jobbergate CLI commands as they play a
significant role in integration testing. For testing you can use the pre-configured user
credentials:

- **Username:** local-user
- **Password:** local

Integration testing should cover the following work-flows:

- Logging in through the CLI
- Creating an Application
- Querying a single Application
- Updating an Application
- Rendering a Job Script from an Application
- Updating a Job Script
- Submitting a Job Script
- Verifying a Job Submission
- Deleting the Job Submission, Job Script, and Application
- Logging out through the CLI

## Setup

To begin, you will need two separate terminals open. Change directory to the
`jobbergate-composed` sub-project of the top-level `jobbergate` folder.

First, you need to start up the Jobbergate platform with docker-compose. In one of your
terminals, run the following command:

```shell
docker-compose up --build
```

Once all the services are started, jump into the prepared `jobbergate-cli` container
to execute CLI commands. To do so, execute this command in the other terminal you have
prepared:

```shell
docker-compose run jobbergate-cli bash
```

Now you may start executing commands with the Jobbergate CLI.

To assist with some of the commands below, create a `NAME` environment variable that
will help to identify resources that you create during the process. You should
set the value based on the current date so that the associated resources are easy to
identify. Run the following command to set it:

```shell
export NAME="test--$(whoami)--$(date -I)"
```

You have now created a test name like `test--tbeck--2023-10-13`.

## Logging in through the CLI

The first work-flow you will test covers the auth mechanics of both the CLI and the API.

Run the following command in the Jobbergate CLI:

```shell
jobbergate login
```

Next, open the link that is printed out and log in as `local-user` (password "local").
If asked, grant all of the permissions.

Verify that the CLI reports that the user has been successfully logged in.

At this point, verify that the token that has been retrieved for the user is correct.

Run the following command in the CLI:

```shell
jobbergate show-token --decode
```

This command will pretty print the payload of the token.
Verify that it contains:

- "view" and "edit" `permissions` for job-templates, job-scripts, and job-submissions
- `email` equalling "<local-user@jobberate.local>"
- `aud` includes "<https://local.omnivector.solutions>"
- `azp` equals "jobbergate-cli"

## Creating an Application

Next, test the command to create an Application through the CLI, and verify that the
resource is created in the database. Also, verify that the files are successfully
uploaded to the file store.

For integration testing, use the built-in
[simple application](https://github.com/omnivector-solutions/jobbergate/tree/main/examples/simple-application).
example. This example application has 3 simple template variables, and, when submitted,
the rendered Job Script simply prints the values of those variables.

Run the following command in the Jobbergate CLI:

```shell
jobbergate applications create --name=$NAME --identifier=$NAME --application-path=/example
```

Verify that output shows that a single application was inserted and that the files were
uploaded:

```plain
                    Created Application
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Key                  ┃ Value                            ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ id                   │ 1                                │
│ name                 │ test--root--2023-10-13           │
│ owner_email          │ local-user@jobbergate.local-mail │
│ is_archived          │ False                            │
│ description          │                                  │
│ identifier           │ test--root--2023-10-13           │
│ application_uploaded │ True                             │
└──────────────────────┴──────────────────────────────────┘
```

## Querying a single Application

Next, verify that we can look up a single Application by both its `id` and its
`identifier`. Also include the `--full` argument to the base `jobbergate` command
so that the output will show all the fields in the database including the source file,
the config, and the timestamps.

First, fetch the Application by `id` using the following command in the CLI:

```shell
jobbergate --full applications get-one --id=1
```

The output should look something like this:

```plain
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Key            ┃ Value                                                                                                                                 ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ id             │ 1                                                                                                                                     │
│ name           │ test--root--2023-10-13                                                                                                                │
│ owner_email    │ local-user@jobbergate.local-mail                                                                                                      │
│ created_at     │ 2023-10-13T19:44:21.935886                                                                                                            │
│ updated_at     │ 2023-10-13T19:44:21.958325                                                                                                            │
│ identifier     │ test--root--2023-10-13                                                                                                                │
│ description    │                                                                                                                                       │
│ template_vars  │ {'bar': 'BAR', 'baz': 'BAZ', 'foo': 'FOO', 'workdir': '/nfs'}                                                                         │
│ template_files │ [{'parent_id': 5, 'filename': 'dummy-script.py.j2', 'file_type': 'ENTRYPOINT', 'created_at': '2023-10-13T19:44:22.020542',            │
│                │ 'updated_at': '2023-10-13T19:44:22.020556'}]                                                                                          │
│ workflow_files │ [{'parent_id': 5, 'filename': 'jobbergate.py', 'runtime_config': {'template_files': None, 'job_script_name': None,                    │
│                │ 'default_template': 'dummy-script.py.j2', 'output_directory': '.', 'supporting_files': None, 'supporting_files_output_name': None},   │
│                │ 'created_at': '2023-10-13T19:44:22.110739', 'updated_at': '2023-10-13T19:44:22.110750'}]                                              │
└────────────────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Verify that the `id`, `name`, `identifier`, and timestamps match the Application
that was created.

Next, fetch the same application by `identifier` and verify that it is the same
Application:

```shell
jobbergate --full applications get-one --identifier=test--tbeck--2023-10-13
```

## Updating an Application

Next, verify that you can update the application through the CLI.

Run this command to verify that we can change the name:

```shell
jobbergate applications update --id=1 --application-desc="Here is a test description"
```

Verify that you can see the new description in the application when you fetch it via the
`get-one` subcommand. Also, check the output with the `--full` parameter to make
sure that the `updated_at` field is different and later than the `created_at` field.

## Rendering a Job Script from an Application

Now that an application has been uploaded uploaded, use it to render a new Job Script.

There are a few different options to test here to check for correct behavior:

- Basic, interactive render
- Render in "fast mode" with a `--param-file`
- Render with additional SBATCH params

### Basic, interactive render

First, render an Application to a Job Script by executing the interactive code that
gathers the values for template variables from the user.

To start the rendering process, execute:

```shell
jobbergate job-scripts render --name=$NAME --application-id=1
```

Verify that you are shown 3 prompts to supply values for the template variables. Fill
these in with any values you like. Notice that the third question has a default response
supplied already. Accept this value or replace it with your preferred value:

```plain
   [?] gimme the foo!: FOO
   [?] gimme the bar!: BAR
   [?] gimme the foo!: BAZ
   [?] gimme the workdir!: /nfs
```

When prompted if you would like to submit the job, decline with "n".

After completing the questions, verify that the CLI reports that the new Job Script was
created using the supplied values:

```plain
                 Created Job Script
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Key            ┃ Value                            ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ id             │ 1                                │
│ application_id │ 1                                │
│ name           │ test--root--2023-10-13           │
│ description    │                                  │
│ owner_email    │ local-user@jobbergate.local-mail │
└────────────────┴──────────────────────────────────┘

```

Now we need to verify that the Job Script was rendered with the correct values. Run the
following command:

```shell
jobbergate job-scripts show-files --id=1
```

The output should show the Job Script with the provided template variable values
rendered as expected:

```plain
╭─────────────────────────────────────────────────────────────────── dummy-script.py ────────────────────────────────────────────────────────────────────╮
│                                                                                                                                                        │
│   #!/bin/python3                                                                                                                                       │
│                                                                                                                                                        │
│   #SBATCH -J dummy_job                                                                                                                                 │
│   #SBATCH -t 60                                                                                                                                        │
│                                                                                                                                                        │
│   print("Executing dummy job script")                                                                                                                  │
│   with open("/nfs/dummy-output.txt", mode="w") as dump_file:                                                                                           │
│       print("I am a very, very dumb job script", file=dump_file)                                                                                       │
│       print("foo=FOO", file=dump_file)                                                                                                                 │
│       print("bar=BAR", file=dump_file)                                                                                                                 │
│       print("baz=BAZ", file=dump_file)                                                                                                                 │
│                                                                                                                                                        │
╰─────────────────────────────────────────────────────────── This is the main job script file ───────────────────────────────────────────────────────────╯
```

### Render in "fast mode" with a `--param-file`

Next, verify that a Job Script can be rendered while skipping the interactive question
answering segment by pre-supplying the application with the values to use for rendering.
Since only the third question has a default, supply at least the other two questions
with a param using the `--param-file` parameter.

First, create a file to hold the params (hit `ctrl-d` to finish and write the file):

```shell
cat > params.json
{
  "foo": "FOO",
  "bar": "BAR"
}
```

Now, render the Application using this file. Include the `--no-submit` flag because
the Job Script shouldn't be submitted immediately. Verify only the rendering process for
the new Job Script:

```shell
jobbergate job-scripts render --name=$NAME --application-id=1 --fast --param-file=params.json --no-submit
```

The output from the command will show you the default values that were used that you did
not specify in the `params.json` file:

```plain
Default values used
┏━━━━━━━━━┳━━━━━━━┓
┃ Key     ┃ Value ┃
┡━━━━━━━━━╇━━━━━━━┩
│ baz     │ zab   │
│ workdir │ /nfs  │
└─────────┴───────┘


                 Created Job Script
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Key            ┃ Value                            ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ id             │ 2                                │
│ application_id │ 1                                │
│ name           │ test--root--2023-10-13           │
│ description    │                                  │
│ owner_email    │ local-user@jobbergate.local-mail │
└────────────────┴──────────────────────────────────┘
```

Now check the rendered file again using the `show-files` sub-command.

### Render with additional SBATCH params

Finally, test that additional `SBATCH` params can be inserted at render time. The code
will insert these additional parameters into the rendered Job Script files.

To supply extra `SBATCH` params, they are provided on the command line using the
`--sbatch-params` option. Use this command to test it out:

```shell
jobbergate job-scripts render --name=$NAME --application-id=1 --fast --param-file=params.json --no-submit --sbatch-params="--cluster=fake" --sbatch-params="--partition=dummy"
```

The output should look like:

```plain
Default values used
┏━━━━━━━━━┳━━━━━━━┓
┃ Key     ┃ Value ┃
┡━━━━━━━━━╇━━━━━━━┩
│ baz     │ zab   │
│ workdir │ /nfs  │
└─────────┴───────┘


                 Created Job Script
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Key            ┃ Value                            ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ id             │ 3                                │
│ application_id │ 1                                │
│ name           │ test--root--2023-10-13           │
│ description    │                                  │
│ owner_email    │ local-user@jobbergate.local-mail │
└────────────────┴──────────────────────────────────┘
```

Now, review the rendered Job Script file using the `--show-files` command. You should
see that the additional two SBATCH parameters are included:

```python
#SBATCH --cluster=fake                                                                                                                               │
#SBATCH --partition=dummy
```

## Updating a Job Script

Next, verify that an existing Job Script can be updated.

Run this command to verify that you can change the description:

```shell
jobbergate job-scripts update --id=1 --description="Here is a test description"
```

Verify that you can see the new description in the Job Script when you fetch it via the
`get-one` subcommand. Also, check the output with the `--full` parameter to make
sure that the `updated_at` field is different and later than the `created_at` field.

## Submitting a Job Script

Next, test the process of submitting a Job Script to a slurm cluster for execution.
Note that the `docker-compose.yaml` used for testing sets up a volume-mounted
directory named `/nfs`. The `/nfs` directory in the container is mounted from the
`slurm-fake-nfs` directory in the `jobbergate-composed` subproject. You can look in this
directory after the job completes execution to check the results.

You will need to verify that jobs are being submitted correctly vai the following steps:

- Submit the job through the CLI
- Verify that the agent submitted the job
- Verify that the agent updates the Job Submission status
- Verify the output from the job

### Submit the job through the CLI

Submit the Job Script using the CLI by running the following command:

```shell
jobbergate job-submissions create --name=$NAME --job-script-id=1 --cluster-name=local-slurm --execution-directory=/nfs
```

Verify that the output shows that the Job Submission has been created for the target
Job Script

```plain
                  Created Job Submission
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Key                 ┃ Value                            ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ id                  │ 1                                │
│ job_script_id       │ 1                                │
│ cluster_name        │ local-slurm                      │
│ slurm_job_id        │ None                             │
│ execution_directory │ /nfs                             │
│ name                │ test--root--2023-10-13           │
│ description         │                                  │
│ owner_email         │ local-user@jobbergate.local-mail │
│ status              │ CREATED                          │
│ report_message      │ None                             │
└─────────────────────┴──────────────────────────────────┘
```

### Verify that the agent submitted the job

To verify that the agent submitted the job correctly, review the log output from the
agent.

The agent performs the following process to complete a Job Submission with Slurm

- Fetch a pending job from the API
- Submit the job to slurm
- Mark the job as submitted and add the slurm job id to it

You can access the log data by running the following command in a terminal that has
changed directory to the `jobbergate-composed` folder:

```shell
docker-compose logs jobbergate-agent
```

It may be useful to pipe the output to a text viewer like `less`.

If the agent has successfully submitted the job, you should see some log lines that
look like this (ellipses indicate omitted content):

```plain
...Retrieved 1 pending job submission...
...Submitting pending job submission 1
...
...Submitting pending job submission 1 to slurm...
...
...Received slurm job id 1 for job submission 1
...Marking job job_submission_id=22 as SUBMITTED (slurm_job_id=1)
```

If you find those log lines, then the Agent has successfully submitted the job to slurm.

### Verify that the job was completed

To verify that the job completed successfully, review the log output from the
agent.

The agent performs the following process to complete Job Submissions

- Fetch the submitted job from the API
- Check the status of the job in slurm using the the `slurm_job_id`
- If the job is completed, mark the Job Submission as COMPLETED

You should look for log lines that look like this (ellipses indicate omitted content):

```plain
...Retrieved 1 active job submissions...
...Fetching status of job_submission 1 from slurm
...Fetching slurm job status for slurm job 1
...
...Status for slurm job 1 is job_id=1 job_state='COMPLETED'...
...Updating job_submission with status=COMPLETED
```

### Verify the output from the job

In the terminal where you are running Jobbergate CLI commands, you can check the `/nfs`
directory to see the results. You should see three output files in the directory:

- test--root--2023-10-13.out
- test--root--2023-10-13.err
- dummy-output.txt

First, check the standard output from the script:

```shell
cat /nfs/test--root--2023-10-13.out
```

You should see a single line that says:

```plain
Executing dummy job script
```

The standard error from the script should be empty.

The final file, `dummy-output.txt`, should contain the following content:

```plain
I am a very, very dumb job script
foo=FOO
bar=BAR
baz=BAZ
```

## Conclusion

The process described in this document covers integration tests across the entire
Jobbergate platform. These integration tests should be performed before new versions of
Jobbergate are published and before Jobbergate is deployed to a new environment.
