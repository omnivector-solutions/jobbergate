======================
 Using Jobbergate CLI
======================

The commands available in ``jobbergate-cli`` revolve around the three core resources of
the system:

* Applications
* Job Scripts
* Job Submissions

.. Note::

   The commands shown here are for the most recent version of Jobbergate. In order to
   use the Jobbergate CLI in "legacy" mode, you need to set the
   ``JOBBERGATE_COMPATIBILITY_MODE`` environment variable to 1. Then, check the usage
   using the ``--help`` for details about the subcommands.


Checking Usage
==============

The usage of the ``jobbergate-cli`` can be checked at any time using the ``--help``
flag. In addition to usage information for the top-level command, ``jobbergate-cli``
also provides ``--help`` usage for each subcommand.

To see the top-level usage, run the following command:

.. code-block:: console

   jobbergate --help
   Usage: jobbergate [OPTIONS] COMMAND [ARGS]...

     Welcome to the Jobbergate CLI!

     More information can be shown for each command listed below by running it
     with the --help option.

   Options:
     --verbose / --no-verbose        Enable verbose logging to the terminal
                                     [default: no-verbose]
     --full / --no-full              Print all fields from CRUD commands
                                     [default: no-full]
     --raw / --no-raw                Print output from CRUD commands as raw json
                                     [default: no-raw]
     --version / --no-version        Print the version of jobbergate-cli and exit
                                     [default: no-version]
     --install-completion [bash|zsh|fish|powershell|pwsh]
                                     Install completion for the specified shell.
     --show-completion [bash|zsh|fish|powershell|pwsh]
                                     Show completion for the specified shell, to
                                     copy it or customize the installation.
     --help                          Show this message and exit.

   Commands:
     applications     Commands to interact with applications
     job-scripts      Commands to interact with job scripts
     job-submissions  Commands to interact with job submissions
     login            Log in to the jobbergate-cli by storing the supplied...
     logout           Logs out of the jobbergate-cli.
     show-token       Show the token for the logged in user.


Logging In
==========

In order to interact with any Jobbergate resources, you first need to log in as a
Jobbergate user.

First, invoke the ``login`` subcommand. You will then be prompted with a browser link to
open in order to login. Open the link in the browser and complete the login process.
When you have finished, the CLI will report that you have successfully logged in:

.. code-block:: console

   jobbergate login

   ╭────────────────────────────────────────────────────────────────── Waiting for login ───────────────────────────────────────────────────────────────────╮
   │                                                                                                                                                        │
   │   To complete login, please open the following link in a browser:                                                                                      │
   │                                                                                                                                                        │
   │     http://keycloak.local:8080/realms/jobbergate-local/device?user_code=BMVJ-NLZS                                                                      │
   │                                                                                                                                                        │
   │   Waiting up to 5.0 minutes for you to complete the process...                                                                                         │
   │                                                                                                                                                        │
   ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

   Waiting for web login... ━╺━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   3% 0:04:50

   ╭────────────────────────────────────────────────────────────────────── Logged in! ──────────────────────────────────────────────────────────────────────╮
   │                                                                                                                                                        │
   │   User was logged in with email 'local-user@jobbergate.local'                                                                                          │
   │                                                                                                                                                        │
   ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯


It is often useful to see the auth token granted upon login. To do this, you can execute
the ``show-token`` command. When running with ``docker-compose`` or over an ssh connection
where clipboard is not shared, you will need to pass the ``--plain`` option to remove
formatting characters and then copy the token to your clipboard manually. The command
looks like this:

.. code-block:: console

   jobbergate show-token --plain
   eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJFVU1BNnBYY0V2VC10U09sSTlrQ3J1ZHktbmtoTzI0VkQyVG92aHp1N2NnIn0.eyJleHAiOjE2NjI3NTc4NjQsImlhdCI6MTY2Mjc1NzU2NCwiYXV0aF90aW1lIjoxNjYyNzU3NTYzLCJqdGkiOiI2YjY3NWNjYS04NGVkLTRiZjYtOTFkNC00ZjlkOTZhNjE4MGYiLCJpc3MiOiJodHRwOi8va2V5Y2xvYWsubG9jYWw6ODA4MC9yZWFsbXMvam9iYmVyZ2F0ZS1sb2NhbCIsImF1ZCI6WyJodHRwczovL2xvY2FsLm9tbml2ZWN0b3Iuc29sdXRpb25zIiwiYWNjb3VudCJdLCJzdWIiOiJiNTgxNjViMC1mNDQyLTRmZDEtYWY0NS05MTZlYzJiYTNhOWEiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJjbGkiLCJzZXNzaW9uX3N0YXRlIjoiMmFjY2Q1M2EtZTY0Yy00ZGI0LWI0MTEtYWE2ZTc3YTY2N2RmIiwiYWNyIjoiMSIsInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJvZmZsaW5lX2FjY2VzcyIsInVtYV9hdXRob3JpemF0aW9uIiwiZGVmYXVsdC1yb2xlcy1qb2JiZXJnYXRlLWxvY2FsIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsiY2xpIjp7InJvbGVzIjpbImpvYmJlcmdhdGU6am9iLXNjcmlwdHM6dmlldyIsImpvYmJlcmdhdGU6am9iLXNjcmlwdHM6ZWRpdCIsImpvYmJlcmdhdGU6YXBwbGljYXRpb25zOmVkaXQiLCJqb2JiZXJnYXRlOmFwcGxpY2F0aW9uczp2aWV3Iiwiam9iYmVyZ2F0ZTpqb2Itc3VibWlzc2lvbnM6dmlldyIsImpvYmJlcmdhdGU6am9iLXN1Ym1pc3Npb25zOmVkaXQiXX0sImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sInNjb3BlIjoicHJvZmlsZSBlbWFpbCIsInNpZCI6IjJhY2NkNTNhLWU2NGMtNGRiNC1iNDExLWFhNmU3N2E2NjdkZiIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwicGVybWlzc2lvbnMiOlsiam9iYmVyZ2F0ZTpqb2Itc2NyaXB0czp2aWV3Iiwiam9iYmVyZ2F0ZTpqb2Itc2NyaXB0czplZGl0Iiwiam9iYmVyZ2F0ZTphcHBsaWNhdGlvbnM6ZWRpdCIsImpvYmJlcmdhdGU6YXBwbGljYXRpb25zOnZpZXciLCJqb2JiZXJnYXRlOmpvYi1zdWJtaXNzaW9uczp2aWV3Iiwiam9iYmVyZ2F0ZTpqb2Itc3VibWlzc2lvbnM6ZWRpdCJdLCJuYW1lIjoiTG9jYWwgVXNlciIsInByZWZlcnJlZF91c2VybmFtZSI6ImxvY2FsLXVzZXIiLCJnaXZlbl9uYW1lIjoiTG9jYWwiLCJmYW1pbHlfbmFtZSI6IlVzZXIiLCJlbWFpbCI6ImxvY2FsLXVzZXJAam9iYmVyZ2F0ZS5sb2NhbCJ9.cNfsslV0rXFcurpndR-kXKtnERn3sfehWPFLNDNFT4s24ifRf1uWlZYGMiwMGj7YkuLv46BDrBHTBMb64Lldsb37-Se1W5ZHeGNRckgkVbVbEaCHmB7hBTf5EJB78JciYqKaoZhRJpENWAwQpvZpjZ5WTedscJPvTcbIegD2e4MCSoG7qya2tnB9yn08QC6vG-aO9qkFzHr7BNVViLvFBzrBO5oc2KGlP8BnTUxzr5O6ork8IYr-PTKQd_zGdNgZiXQuB10LPYUYaCnji6biaMSApp2Dukrc1FQPlpiQ_Zbku00tJ0tQDtdVQHxEsjncXuXNI_oRTDSVXyuxnwxEmQ



Application Commands
====================

You may interact with Jobbergate Application resources using the ``applications``
subommand.

The following sub-commands are available for ``applications``:

* create
* delete
* get-one
* list
* update

Details for each subcommand can be viewed by passing the ``--help`` flag to any of them.

Example: Creating an Application:

.. code-block:: console

   jobbergate applications create --name test-application --application-path /path/to/application


JobScript Commands
==================

You may interact with Jobbergate Job Script resources using the ``job-scripts``
subcommand.

The following sub-commands are available for ``job-scripts``:

* create
* delete
* get-one
* list
* update

Details for each subcommand can be viewed by passing the ``--help`` flag to any of them.

Example: Rendering an Application into a new Job Script:

.. code-block:: console

   jobbergate job-sripts create --application-id=1 --name test-job-script


JobSubmission Commands
======================

You may interact with Jobbergate Job Submission resources using the ``job-submissions``
subcommand.

The following sub-commands are available for ``job-submissions``:

* create
* delete
* get-one
* list

Details for each subcommand can be viewed by passing the ``--help`` flag to any of them.

Example: Submitting a Job Script as a new Job Submission:

.. code-block:: console

   jobbergate job-sripts create --job-script-id=1 --name test-job-submission --cluster-name test-cluster

.. _examples: https://github.com/omnivector-solutions/jobbergate/tree/main/examples
