=======
 Usage
=======

To start using ``jobbergate-cli``, it is first necessary login as a user. This can be don by passing
the ``username`` (usually an email address) and ``password`` as options to the main ``jobbergate``
command.  If credentials are not provided on the command-line, they will be gathered from the user
in an interactive session. Users may also supply their credentials via the environment variables
"JOBBERGATE_PASSWORD" and "JOBBERGATE_PASSWORD".

Once a user has logged in, their credentials will be cached for future commands. The credentials
will automatically expire after some period of time, and you will need to log in again unless you
supplied your credentials via environment variable.

The commands available in ``jobbergate-cli`` revolve around the three core resources of the system.

To see a list of available commands, invoke the ``jobbergate-cli`` with the ``--help`` option::

    $ jobbergate --help

    Usage: jobbergate [OPTIONS] COMMAND [ARGS]...

      Jobbergate CLI.

      Provides a command-line interface to the Jobbergate API. Available commands
      are listed below. Each command may be invoked with --help to see more
      details and available parameters.

      If you have not logged in before and you do not include the --username and
      --password options, you will be prompted for your login info. Your
      credentials will then be securely saved for use in subsequent commands so
      you do not need to supply them again. Saved credentials will automatically
      expire after some time.

    Options:
      -u, --username TEXT  Your Jobbergate API Username
      -p, --password TEXT  Your Jobbergate API password
      -v, --verbose        Enable verbose logging to the terminal
      --version            Show the version and exit.
      --help               Show this message and exit.

    Commands:
      create-application     CREATE an application.
      create-job-script      CREATE a Job Script.
      create-job-submission  CREATE Job Submission.
      delete-application     DELETE an Application.
      delete-job-script      DELETE a Job Script.
      delete-job-submission  DELETE a Job Submission.
      get-application        GET an Application.
      get-job-script         GET a Job Script.
      get-job-submission     GET a Job Submission.
      list-applications      LIST the available applications.
      list-job-scripts       LIST Job Scripts.
      list-job-submissions   LIST Job Submissions.
      logout                 Logs out of the jobbergate-cli.
      update-application     UPDATE an Application.
      update-job-script      UPDATE a Job Script.
      update-job-submission  UPDATE a Job Submission.
      upload-logs            Uploads user logs to S3 for analysis.



Application Commands
====================

The following commands are available for interacting with the ``Application`` resource:

* create-application
* list-applications
* get-application
* delete-application


Create an Application
---------------------

To create a basic `Application`, invoke a command like this with the `jobbergate-cli`::

    $ jobbergate create-application --name test-application --application-path /path/to/application


The ``name`` and the ``application-path`` are required to create an ``application``.  The ``application-path``
describes the path to an application directory containing application code, configuration, and templates.
An example application can be found in a github repo called `"jobbergate-test-application"
<https://github.com/omnivector-solutions/jobbergate-test-application>`_

Remember that if a user has not yet authenticated with ``jobbergate-cli`` you will need to supply your
username and password.

If everything is successful, ``jobbergate-cli`` will print the following to your terminal::

    -----------------------  ----------------
    application_name         test-application
    application_description
    application_owner_id     1
    id                       1
    -----------------------  ----------------


List Available Applications
---------------------------

To list the available ``Applications``, type the following command::

    $ jobbergate list-applications

The ``jobbergate-cli`` will print a list with all the ``Applications`` from the user.
Here is an example::

    application_name    application_description      application_owner_id    id
    ------------------  -------------------------  ----------------------  ----
    test-application    description                                     1     1

It is also possible to use the ``--all`` flag to list all applications, even those created
by other users.


Get an Application
------------------

To get a detailed view of a single ``Application``, the ``get-application`` command may be
issued with the ``Apllication`` id::

    $ jobbergate get-application --id 1
    -----------------------  ---------------------------------------------------------------------
    id                       1
    application_name         test-application
    application_description
    application_location     jobbergate-resources/1/applications/1/jobbergate.tar.gz
    application_owner        1
    application_file         from jobbergate_cli.application_base import JobbergateApplicationBase
                             from jobbergate_cli import appform

                             # cory

                             class JobbergateApplication(JobbergateApplicationBase):

                                 def mainflow(self, data):
                                     questions = []

                                     questions.append(appform.List(
                                         variablename="partition",
                                         message="Choose slurm partition:",
                                         choices=self.application_config['partitions'],
                                     ))

                                     questions.append(appform.Text(
                                         variablename="job_name",
                                         message="Please enter a jobname",
                                         default=self.application_config['job_name']
                                     ))
                                     return questions
    application_config       application_config:
                               job_name: rats
                               partitions:
                               - juju-compute-SCqp
                             jobbergate_config:
                               default_template: test_job_script.sh
                               output_directory: .
                               supporting_files:
                               - test_job_script.sh
                               supporting_files_output_name:
                                 test_job_script.sh:
                                 - support_file_b.py
                               template_files:
                               - templates/test_job_script.sh
    application_identifier   test-application
    created_at               2021-10-28T00:15:08.983712Z
    updated_at               2021-10-28T00:15:08.983737Z
    -----------------------  ---------------------------------------------------------------------


Delete an Application
---------------------

To delete an ``Application``, use the ``delete-application`` command with the target ``Application`` id::

    $ jobbergate delete-application --id 1

If the ``Application`` exists, and the ``User`` has the permission to delete it, ``jobbergate-cli`` will
deleted the ``Application`` and all the information related to it. This includes any ``JobScripts`` that
were created from the ``Application``

This action will not print any information if the deletion was successful.


JobScript Commands
==================

The following commands are avaialble for interacting with the ``JobScript`` resource:

* create-job-script
* list-job-scripts
* get-job-script
* delete-job-script


Create a JobScript
------------------

To create a ``JobScript``, an ``Application`` must already exist. because each ``JobScript`` is generated
using an ``Application``. The ``create-job-script`` command must, therefore, be invoked with the
target ``Application`` id::

    $ jobbergate create-job-script --application-id 1

When this command is ran, it will ask the user to supply answers to qustions defined in the ``Application``.

To illustrate, if the ``Application`` created was using the supplied example application it will use the
`jobbergate.py <https://github.com/omnivector-solutions/jobbergate-test-application/blob/main/jobbergate.py>`_
file from `the example GitHub repository <https://github.com/omnivector-solutions/jobbergate-test-application>`_
to generate the questions for rendering the ``JobScript`` template together with the configuration options
described in `jobbergate.yaml
<https://github.com/omnivector-solutions/jobbergate-test-application/blob/main/jobbergate.yaml>`.

The ``jobbergate-cli`` will prompt users for answers in this manner::

    [?] Choose slurm partition: debug
     > debug
       partition1

    [?] Please enter a jobname: rats

For the first question it is necessary to choose the disired partition with the arrows keys. For the second it
is possible to use the default supplied name, but it is may be changed to something that fits better.

In the next step ``jobbergate-cli`` will ask the following::

    [?] Would you like to submit this immediately? (Y/n):

This is asking if the submitted ``JobScript`` can be submitted right away as a ``JobSubmission`` to run in the cluster.
If the answer is ``yes``, then it will create the ``JobSubmission`` and submit the ``JobScript`` to Slurm for execution
on the cluster. If the answer is ``no``, then it will only create the ``JobScript`` instance in the database.


List Available JobScripts
-------------------------

To list the available ``JobScripts``, type the following command::

    $ jobbergate list-job-script

The ``jobbergate-cli`` will print a list with all the ``JobScript`` entries created by the current user.

Here is an example:

.. code-block::

      id  job_script_name      job_script_description      job_script_owner    application
    ----  -------------------  ------------------------  ------------------  -------------
       1  default_script_name  TEST_DESC                                  1              1


It is also possible to use the ``--all`` flag to list all ``JobScript`` entries, even those created
by other users.


Get a JobScript
---------------

To get a detailed view of a single ``JobScript``, the ``get-job-script`` command may be
issued with the ``JobScript`` id::

    $ poetry run jobbergate get-job-script --id=1

    -------------------------  ------------------------------
    id                         1
    job_script_name            default_script_name
    job_script_description     TEST_DESC
    job_script_data_as_string  NEW_FILE
                               #!/bin/bash

                               #SBATCH --job-name=star
                               #SBATCH --partition=debug
                               #SBATCH --output=sample-%j.out


                               echo $SLURM_TASKS_PER_NODE
                               echo $SLURM_SUBMIT_DIR
                               echo $SLURM_NODE_ALIASES
                               echo $SLURM_CLUSTER_NAME
                               echo $SLURM_JOB_CPUS_PER_NODE
                               echo $SLURM_JOB_PARTITION
                               echo $SLURM_JOB_NUM_NODES
                               echo $SLURM_JOBID
                               echo $SLURM_NODELIST
                               echo $SLURM_NNODES
                               echo $SLURM_SUBMIT_HOST
                               echo $SLURM_JOB_ID
                               echo $SLURM_CONF
                               echo $SLURM_JOB_NAME
                               echo $SLURM_JOB_NODELIST
    job_script_owner           1
    application                1
    created_at                 2021-10-27T21:43:41.821331Z
    updated_at                 2021-10-27T21:43:41.821358Z
    -------------------------  ------------------------------

The information printed out includes a complete description of the ``JobScript`` including the rendered script
itself.


Delete a JobScript
------------------

To delete a ``JobScript``, use the ``delete-job-script`` command with the target ``JobScript`` id::

    $ jobbergate delete-job-script --id=1

If the ``JobScript`` exists, and the ``User`` has the permission to delete it, ``jobbergate-cli`` will
deleted the ``JobScript`` and all the information related to it. This action will not print any
information if the deletion was successful.


JobSubmission Commands
======================

The following commands are avaialble for interacting with the ``JobSubmission`` resource:

* create-job-submission
* list-job-submission
* get-job-submission
* delete-job-submission


Create a JobSubmission
----------------------

To create a ``JobSubmission``, a ``JobScript`` must already exist, because each ``JobSubmission`` involves
submitting a ``JobScript`` to Slurm for execution. The ``create-job-script`` command must, therefore, be
invoked with the target ``JobScript`` id::

    $ jobbergate create-job-submission --name=test-submission-1 --job-script-id=1
    Submitted batch job 1


    --------------------------  ---------------------------
    id                          1
    job_submission_name         test-submission-1
    job_submission_description  TEST_DESC
    job_submission_owner        1
    job_script                  1
    slurm_job_id                1
    created_at                  2021-10-28T00:19:44.224243Z
    updated_at                  2021-10-28T00:19:44.224265Z
    --------------------------  ---------------------------

The output shows that the job has been submitted via Slurm and now has a slurm job identifier that
can be used to interact with Slurm regarding the job if you need.

Further, you may supply the ``--dry-run`` flag if you only want to see what the submission would do without
actually submitting the job.  This will only create entries in the database without submitting the job to Slurm.,
you may use the ``--dry-run`` option.


List Active JobSubmissions
--------------------------

To list the available ``JobSubmissions``, type the following command::

    $ jobbergate list-job-submissions

The ``jobbergate-submissons`` command will print a list with all the ``JobSubmission`` entries created by
the current user.

Here is an example of the output:

.. code-block::

      id  job_submission_name    job_submission_description      job_submission_owner    job_script  slurm_job_id
    ----  ---------------------  ----------------------------  ----------------------  ------------  --------------
       1  test-submission-1      TEST_DESC                                          1             1               1

It is also possible to use the ``--all`` flag to list all ``JobSubmission`` entries, even those created
by other users.


Get a JobSubmision
------------------

To get a detailed view of a single ``JobSubmission``, the ``get-job-submission`` command may be
issued with the ``JobApplication`` id::

    $ poetry run jobbergate get-job-submission --id=1

    --------------------------  ---------------------------
    id                          1
    job_submission_name         test-submisson-1
    job_submission_description  TEST_DESC
    job_submission_owner        1
    job_script                  1
    slurm_job_id                1
    created_at                  2021-10-28T00:19:44.224243Z
    updated_at                  2021-10-28T00:19:44.224265Z
    --------------------------  ---------------------------

The information printed out includes a complete description of the ``JobSubmission`` including the Slurm job id
associated with it.


Delete a JobSubmission
----------------------

To delete a ``JobSubmission``, use the ``delete-job-submission`` command with the target ``JobSubmission`` id::

    $ jobbergate delete-job-submission --id=1

If the ``JobSubmission`` exists, and the ``User`` has the permission to delete it, ``jobbergate-cli`` will
deleted the ``JobSubmission``. This action will not print any information if the deletion was successful.
