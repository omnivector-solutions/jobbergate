=====================
 Integration Testing
=====================

When you integration testi Jobbergate, it is essential that you test the full cycle of
the platfrom from Application creation to remote Job Submission through the Cluster
Agent.

For most changes, it is adequate for you to use the ``docker-compose`` configuration
found in the `Jobbergate Composed <https://github.com/omnivector-solutions/jobbergate/jobbergate-composed>`_
subproject. Start with the guide on that subproject's README. Take note of how to
exeucte the Jobbergate CLI commands as they will be used extensively in the intergration
testing. You may use the automatically created user for testing
(username: "local-user", password: "local").

The integration testing should cover the following work-flows:

* Logging in through the CLI
* Creating an Application
* Querying a single Application
* Updating an Application
* Rendering a Job Script from an Application
* Updating a Job Script
* Submitting a Job Script
* Verifying a Job Submission
* Deleting the Job Submission, Job Script, and Application
* Logging out through the CLI


Setup
-----

First, start up the Jobbergate system in docker-compose. Navigate to the
``jobbergate-composed`` subproject and run the following command:

.. code-block:: console

   docker-compose up --build

Once all the services are started, jump into the prepared ``jobbergate-cli`` container
to execute CLI commands. To do so, open a new terminal in the ``jobbergate-composed``
subproject and run the following command:

.. code-block:: console

   docker-compose run jobbergate-cli bash

Now you may start executing commands with the Jobbergate CLI.

To assist with some of the commands below, create a ``NAME`` environment variable that
can you may use to help identify resource that you create during the process. You should
set the value based on the current date so that the associated resources are easy to
identify. Run the following command to set it:

.. code-block:: console

   export NAME="test--$(whoami)--$(date -I)"

You have now created a test name like "test--tbeck--2022-09-02".


Logging in through the CLI
--------------------------

The first work-flow you will test covers the auth mechanics of both the CLI and the API.

Run the following command in the CLI:

.. code-block:: console

   jobbergate login

Next, open the link that is printed out and log in as ``local-user`` (password "local").
If asked, grant all of the permissions.

Verify that the CLI reports that the user has been successfully logged in.

At this point, verify that the token that has been retrieved for the user is correct.

Run the following command in the CLI:

.. code-block:: console

   jobbergate show-token --plain

Copy the text of the token that is printed to the screen, navigate to
`jwt.io <https://jwt.io>`_, and paste the token into the "Encoded" box. Then, check the
"Payload" output and verify that it contains:

* "view" and "edit" ``permissions`` for applications, job-scripts, and job-submissions
* ``email`` equalling "local-user@jobberate.local"
* ``aud`` includes "https://local.omnivector.solutions"
* ``azp`` equals "jobbergate-cli"


Creating an Application
-----------------------

Next, test the command to create an Application through the CLI, and verify that the
resource is created in the database. Als, verify that the files are successfully
uploaded to the file store.

For integration testing, use the built-in
`example application <https://github.com/omnivector-solutions/jobbergate/tree/main/examples/application-example>`_.
This example application has 3 simple template variables, and, when submitted, the
rendered Job Script simply prints the values of those variables.

Run the following command in the CLI:

.. code-block:: console

   jobbergate applications create --name=$NAME --identifier=$NAME --application-path=/example


Verify that output shows that a single application was inserted and that the files were
uploaded::

                         Created Application
   ┏━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
   ┃ Key                     ┃ Value                       ┃
   ┡━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
   │ id                      │ 1                           │
   │ application_name        │ test--tbeck--2022-09-02     │
   │ application_identifier  │ test--tbeck--2022-09-02     │
   │ application_description │                             │
   │ application_owner_email │ local-user@jobbergate.local │
   │ application_uploaded    │ True                        │
   └─────────────────────────┴─────────────────────────────┘


Querying a single Application
-----------------------------

Next, verify that we can look up a single pplication by both its ``id`` and it's
``identifier``. Also include the ``--full`` argument to the base ``jobbergate`` command
so that the output will show all the fields in the database including the source file,
the config, and the timestamps.

First, fetch the Application by ``id`` using the following command in the CLI:

.. code-block:: console

   jobbergate --full applications get-one --id=1

The output should look something like this::

   ┏━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
   ┃ Key                     ┃ Value                                                                                         ┃
   ┡━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
   │ id                      │ 1                                                                                             │
   │ application_name        │ test--tbeck--2022-09-02                                                                       │
   │ application_identifier  │ test--tbeck--2022-09-02                                                                       │
   │ application_description │                                                                                               │
   │ application_owner_email │ local-user@jobbergate.local                                                                   │
   │ application_uploaded    │ True                                                                                          │
   │ created_at              │ 2022-09-02 21:54:47.809237                                                                    │
   │ updated_at              │ 2022-09-02 22:05:27.580963                                                                    │
   │ application_config      │ jobbergate_config:                                                                            │
   │                         │   default_template: dummy-script.py.j2                                                        │
   │                         │   output_directory: .                                                                         │
   │                         │ application_config:                                                                           │
   │                         │   foo: FOO                                                                                    │
   │                         │   bar: BAR                                                                                    │
   │                         │   baz: BAZ                                                                                    │
   │                         │                                                                                               │
   │ application_source_file │ from jobbergate_cli.subapps.applications.application_base import JobbergateApplicationBase    │
   │                         │ from jobbergate_cli.subapps.applications.questions import Text                                │
   │                         │                                                                                               │
   │                         │                                                                                               │
   │                         │ class JobbergateApplication(JobbergateApplicationBase):                                       │
   │                         │                                                                                               │
   │                         │     def mainflow(self, data=None):                                                            │
   │                         │         if data is None:                                                                      │
   │                         │             data=dict()                                                                       │
   │                         │         data["nextworkflow"] = "subflow"                                                      │
   │                         │         return [Text("foo", message="gimme the foo!"), Text("bar", message="gimme the bar!")] │
   │                         │                                                                                               │
   │                         │     def subflow(self, data=None):                                                             │
   │                         │         if data is None:                                                                      │
   │                         │             data=dict()                                                                       │
   │                         │         return [Text("baz", message="gimme the baz!", default="zab")]                         │
   │                         │                                                                                               │
   └─────────────────────────┴───────────────────────────────────────────────────────────────────────────────────────────────┘

Verify that the ``id``, ``name``, ``identifier``, and timestamps match the Applicaiton
that was created.

Next, fetch the same application by ``identifier`` and verify that it is the same
Application:

.. code-block:: console

   jobbergate --full applications get-one --identifier=test--tbeck--2022-09-02


Updating an Application
-----------------------

Next, verify that you can update the application through the CLI.

Run this command to verify that we can change the name:

.. code-block:: console

   jobbergate applications update --id=1 --application-desc="Here is a test description"

Verify that you can see the new description in the application when you fetch it via the
``get-one`` subcommand. Also, check the output with the ``--full`` parameter to make
sure that the ``updated_at`` field is different and later than the ``created_at`` field.


Rendering a Job Script from an Application
------------------------------------------

Now that an application has been uploaded uploaded, use it to render a new Job Script.

There are a few differnt options to test here to make sure they are working correctly:

* Basic, interactive render
* Render in "fast mode" with a ``--param-file``
* Render with additional SBATCH params


Basic, interactive render
.........................

First, render an Applicaiton to a Job Script by executing the interactive code that
gathers the values for template variables from the user.

To start the renderin process, execute:

.. code-block:: console

   jobbergate job-scripts create --name=$NAME --application-id=1

Verify that you are shown 3 prompts to supply values for the template variables. Fill
these in with any values you like. Notice that the third question has a default response
supplied already. Accept this value or replace it with your preferred value::

   [?] gimme the foo!: FOO
   [?] gimme the bar!: BAR
   [?] gimme the foo!: BAZ


After completing the questions, verify that the CLI reports that the new Job Script was
created using the supplied values. Decline to submit the job immediately::

                                                                       Created Job Script
   ┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
   ┃ Key                    ┃ Value                                                                                                                         ┃
   ┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
   │ id                     │ 1                                                                                                                             │
   │ application_id         │ 1                                                                                                                             │
   │ job_script_name        │ test--tbeck--2022-09-02                                                                                                        │
   │ job_script_description │ None                                                                                                                          │
   │ job_script_files       │ {'main_file_path': PosixPath('dummy-script.py'), 'files': {PosixPath('dummy-script.py'): '#!/bin/python3\n\n#SBATCH -J        │
   │                        │ dummy_job\n#SBATCH -t 60\n\nprint("I am a very, very dumb job                                                                 │
   │                        │ script")\nprint("foo=FOO")\nprint("bar=BAR")\nprint("baz=BAZ")'}}                                                             │
   │ job_script_owner_email │ local-user@jobbergate.local                                                                                                   │
   └────────────────────────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

   Would you like to submit this job immediately? [y/N]:

Notice here that the values in the ``job_script_files`` have been filled in with the
answers you provided in the question answering segment.


Rener in "fast mode" with a ``--param-file``
............................................

Next, verify that a Job Script can be rendered while skipping the interactive question
answering segment by pre-supplying the application with the values to use for rendering.
Since only the third question has a default, supply at least the other two questions
with a param using the ``--param-file`` parameter.

First, create a file to hold the params (hit ``ctrl-d`` to finish and write the file):

.. code-block:: console

   cat > params.yaml
   foo: FOO
   bar: BAR

Now, render the Application using this file. Include the ``--no-submit`` flag because
the Job Script shouldn't be submitted immediately. Verify only the rendering process for
the new Job Script:

.. code-block:: console

   jobbergate job-scripts create --name=$NAME --application-id=1 --fast --param-file=params.json --no-submit

   Default values
        used
   ┏━━━━━┳━━━━━━━┓
   ┃ Key ┃ Value ┃
   ┡━━━━━╇━━━━━━━┩
   │ baz │ zab   │
   └─────┴───────┘


                                                                       Created Job Script
   ┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
   ┃ Key                    ┃ Value                                                                                                                         ┃
   ┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
   │ id                     │ 2                                                                                                                             │
   │ application_id         │ 1                                                                                                                             │
   │ job_script_name        │ test--tbeck--2022-09-02                                                                                                        │
   │ job_script_description │ None                                                                                                                          │
   │ job_script_files       │ {'main_file_path': PosixPath('dummy-script.py'), 'files': {PosixPath('dummy-script.py'): '#!/bin/python3\n\n#SBATCH -J        │
   │                        │ dummy_job\n#SBATCH -t 60\n\nprint("I am a very, very dumb job                                                                 │
   │                        │ script")\nprint("foo=FOO")\nprint("bar=BAR")\nprint("baz=zab")'}}                                                             │
   │ job_script_owner_email │ local-user@jobbergate.local                                                                                                   │
   └────────────────────────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘



Render with additional SBATCH params
....................................

Finally, test that additional ``SBATCH`` params can be inserted at render time. The code
will insert these additional paramters into the rendered ``job_script_files``.

Run the following command to check for this. Note that multiple sbatch params must each
be passed to a separate argument:

.. code-block:: console

   jobbergate job-scripts create --name=$NAME --application-id=1 --fast --param-file=params.json --no-submit --sbatch-params="--cluster=fake" --sbatch-params="--partition=dummy"

   Default values
        used
   ┏━━━━━┳━━━━━━━┓
   ┃ Key ┃ Value ┃
   ┡━━━━━╇━━━━━━━┩
   │ baz │ zab   │
   └─────┴───────┘


                                                                       Created Job Script
   ┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
   ┃ Key                    ┃ Value                                                                                                                         ┃
   ┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
   │ id                     │ 1                                                                                                                             │
   │ application_id         │ 1                                                                                                                             │
   │ job_script_name        │ test--tbeck--2022-09-02                                                                                                        │
   │ job_script_description │ None                                                                                                                          │
   │ job_script_files       │ {'main_file_path': PosixPath('dummy-script.py'), 'files': {PosixPath('dummy-script.py'): '#!/bin/python3\n\n#SBATCH -J        │
   │                        │ dummy_job\n#SBATCH --cluster=fake\n#SBATCH --partition=dummy\n#SBATCH -t 60\n\nprint("I am a very, very dumb job              │
   │                        │ script")\nprint("foo=FOO")\nprint("bar=BAR")\nprint("baz=zab")'}}                                                             │
   │ job_script_owner_email │ local-user@jobbergate.local                                                                                                   │
   └────────────────────────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

Verify that the params have been injected into the ``job_script_files`` at the
appropriate location.



Updating a Job Script
---------------------

Next, verify that an existing Job Script can be updated.

Run this command to verify that you can change the description:

.. code-block:: console

   jobbergate job-scripts update --id=1 --description="Here is a test description"

Verify that you can see the new description in the Job Script when you fetch it via the
``get-one`` subcommand. Also, check the output with the ``--full`` parameter to make
sure that the ``updated_at`` field is different and later than the ``created_at`` field.


Submitting a Job Script
-----------------------

Next, test the process of submitting a Job Script to a slurm cluster for execution.
Note that the ``docker-compose.yaml`` used for testing sets up a volume-mounted
directory named ``slurm-exec-dir``. Target this directory as the
``--execution-directory`` option so that the output file can be checked post execution.

Verify that jobs are being submitted correctly with the following steps:

* Submit the job through the CLI
* Verify that the agent submitted the job
* Verify that the agent updates the Job Submission status
* Verify the output from the job

Submit the job through the CLI
..............................

Submit the Job Script using the CLI by running the following command:

.. code-block:: console

   jobbergate job-submissions create --name=$NAME --job-script-id=1 --cluster-name=local-slurm --execution-directory=/slurm-exec-dir

Verify that the output shows that the Job Submission has been created for the target
Job Script::


                      Created Job Submission
   ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
   ┃ Key                        ┃ Value                       ┃
   ┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
   │ id                         │ 1                           │
   │ job_script_id              │ 1                           │
   │ client_id                  │ local-slurm                 │
   │ slurm_job_id               │ None                        │
   │ execution_directory        │ /slurm-exec-dir             │
   │ job_submission_name        │ test--tbeck--2022-09-02     │
   │ job_submission_description │ None                        │
   │ job_submission_owner_email │ local-user@jobbergate.local │
   │ status                     │ CREATED                     │
   └────────────────────────────┴─────────────────────────────┘


Verify that the agent submitted the job
.......................................

To verify that the agent submitted the job correctly, review the log output from the
agent.

The agent performs X operations in the process of performing Jobbergate tasks on the
cluster::

* Fetch pending jobs from the API
* Submit pending jobs to Slurm
* Mark jobs as submitted
* Mark jobs as completed or failed

