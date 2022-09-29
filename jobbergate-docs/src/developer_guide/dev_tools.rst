===============
 API Dev Tools
===============

The Jobbergate API application ships with a few developer helper tools that add some
convenient ways to set up or interact with the API

Invoking ``dev-tools``
----------------------

The ``dev-tools`` are invoked as scripts in the Jobbergate API environment created and
maintained by Poetry.

To invoke the dev tools, you must execute the commands from the home directory for the
``jobbergate-api``. Then, run the ``dev-tools`` script with Poetry:

.. code-block:: console

   poetry run dev-tools --help

   Usage: dev-tools [OPTIONS] COMMAND [ARGS]...

   Options:
     --install-completion [bash|zsh|fish|powershell|pwsh]
                                     Install completion for the specified shell.
     --show-completion [bash|zsh|fish|powershell|pwsh]
                                     Show completion for the specified shell, to
                                     copy it or customize the installation.
     --help                          Show this message and exit.

   Commands:
     db
     dev-server  Start a development server locally.
     show-env    Print out the current environment settings.


The ``db`` subcommand
---------------------

There are a few convenience methods in the ``dev-tools`` for interacting with the
Jobbergate API's postgres database. These tools are found in the ``db`` subcommand:

.. code-block:: console

   poetry run dev-tools db --help


The ``start`` subcommand
........................

This command is used to start up a database in docker that is configured using the
values found in the execution environment for Jobbergate.

To start a development database, invoke this command:

.. code-block:: console

   poetry run dev-tools db start

Note that the values for the database name, host, port, and password will all be
gathered from the environment. The sript shold produce some logging output that will
indicate the status of the db::

   2022-09-07 15:44:56.634 | DEBUG    | dev_tools.db:start:57 - Starting dev-jobbergate-postgres with:
   {
     "image": "postgres:14.1",
     "env": {
       "POSTGRES_PASSWORD": "compose-db-pswd",
       "POSTGRES_DB": "compose-db-name",
       "POSTGRES_USER": "compose-db-user"
     },
     "ports": {
       "5432/tcp": 5432
     }
   }
   2022-09-07 15:44:56.634 | DEBUG    | docker_gadgets.gadgets:start_service:19 - Starting service 'dev-jobbergate-postgres'
   2022-09-07 15:44:56.642 | DEBUG    | docker_gadgets.gadgets:start_service:26 - Retrieving external image for dev-jobbergate-postgres using postgres:14.1
   2022-09-07 15:44:56.649 | DEBUG    | docker_gadgets.helpers:get_image_external:43 - Pulling postgres:14.1 image (tag='14.1')
   2022-09-07 15:45:03.190 | DEBUG    | docker_gadgets.helpers:cleanup_container:13 - Checking for existing container: dev-jobbergate-postgres
   2022-09-07 15:45:03.195 | DEBUG    | docker_gadgets.helpers:cleanup_container:24 - No existing container found: dev-jobbergate-postgres
   2022-09-07 15:45:03.196 | DEBUG    | docker_gadgets.gadgets:start_service:31 - Checking if needed ports {'5432/tcp': 5432} are available
   2022-09-07 15:45:03.217 | DEBUG    | docker_gadgets.gadgets:start_service:34 - Starting container: dev-jobbergate-postgres
   2022-09-07 15:45:03.647 | DEBUG    | docker_gadgets.gadgets:start_service:48 - Started container: dev-jobbergate-postgres (<Container: e686e97595>)

In this example, the container name is ``dev-jobbergate-postgres`` and it is running in
the docker container referenced by ``e686e97595`` with the port 5432 mapped from
the host machine to the container.

This command is also very convenient for starting up a database for unit testing. To do
so, you need only pass the ``--test`` flag.

The ``start-all`` subcommand
............................

This command is just a convenient way of spinning up both a development database and a
test database in one command. It is equivalent to running the following two commands in
succession:

.. code-block:: console

   poetry run dev-tools db start


.. code-block:: console

   poetry run dev-tools db start --test


The ``login`` subcommand
........................

This command allows you to log in to the database that your Jobbergate API execution
environment is configured to connect with. Whether the database is hosted locally in
docker or on a remote postrges server, this command will let you log into any database
that your Jobbergate API can connect with.

To log in to the database, execute this command:

.. code-block:: console

   poetry run dev-tools db login


The command will show some debug output including the URL of the database to which it is
connecting and will then show a REPL connection to the database::

   $ poetry run dev-tools db login
   2022-09-07 15:52:02.089 | DEBUG    | dev_tools.db:login:26 - Logging into database: postgresql://compose-db-user:compose-db-pswd@localhost:5432/compose-db-name
   Server: PostgreSQL 14.1 (Debian 14.1-1.pgdg110+1)
   Version: 3.4.1
   Home: http://pgcli.com
   compose-db-name>


The ``migrate`` subcommand
..........................


This command uses `alembic`_ to generate a migration script to bring the current
database (described by the environment) up to date with the `SQLAlchemy`_ models
specified in the Jobbergate API source code.

To invoke the migration script generation, execute:

.. code-block:: console

   poetry run dev-tools db migrate --message="An example migration"


Some logging infow will be produced, including the location of the new migration script::

  2022-09-07 15:58:09.725 | DEBUG    | dev_tools.db:migrate:79 - Creating migration with message: An example migration
  INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
  INFO  [alembic.runtime.migration] Will assume transactional DDL.
  INFO  [alembic.ddl.postgresql] Detected sequence named 'applications_id_seq' as owned by integer column 'applications(id)', assuming SERIAL and omitting
  INFO  [alembic.ddl.postgresql] Detected sequence named 'job_scripts_id_seq' as owned by integer column 'job_scripts(id)', assuming SERIAL and omitting
  INFO  [alembic.ddl.postgresql] Detected sequence named 'job_submissions_id_seq' as owned by integer column 'job_submissions(id)', assuming SERIAL and omitting
    Generating /home/dusktreader/git-repos/omnivector/jobbergate/jobbergate-api/alembic/versions/20220907_155809--c275de463a90_an_example_migration.py ...  done
    Running post write hook "black" ...
  reformatted /home/dusktreader/git-repos/omnivector/jobbergate/jobbergate-api/alembic/versions/20220907_155809--c275de463a90_an_example_migration.py

  All done! ✨ 🍰 ✨
  1 file reformatted.
    done
    Running post write hook "isort" ...
  Fixing /home/dusktreader/git-repos/omnivector/jobbergate/jobbergate-api/alembic/versions/20220907_155809--c275de463a90_an_example_migration.py
    done

The generated migration should *always* be reviewed before it is committed to the
repository.

It is also possible to produce a blank migration if you need to execute some raw SQL or
write an Alembic script by hand. Just pass the ``--blank`` parameter on the command
line:

.. code-block:: console

   poetry run dev-tools db migrate --blank --message="A blank migration"

The ``upgrade`` subcommand
..........................

This subcommand is used to apply a database migration to the database that the
Jobbergate API is configured to connect with.

By default, it will apply all the migrations that have not yet been applied to the
database.

To apply the migrations, execute the command:

.. code-block:: console

   poetry run dev-tools db upgrade


It will produce some logging output that shows what migrations were applied::

   2022-09-07 16:05:46.315 | DEBUG    | dev_tools.db:upgrade:89 - Upgrading database...
   INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
   INFO  [alembic.runtime.migration] Will assume transactional DDL.
   INFO  [alembic.runtime.migration] Running upgrade d22da0741b7f -> c275de463a90, An example migration


If you wish to only upgrade the database *to* a speicifc migration, you can pass that
migration's id to the ``--target`` param.


The ``show-env`` subcommand
---------------------------

This command will show how the Jobbergate API is configured through its environment
settings. To see the environment, execute this command:

.. code-block:: console

   poetry run dev-tools show-env
   Jobbergate settings:
     DEPLOY_ENV: LOCAL
     LOG_LEVEL: DEBUG
     DATABASE_HOST: localhost
     DATABASE_USER: compose-db-user
     DATABASE_PSWD: compose-db-pswd
     DATABASE_NAME: compose-db-name
     DATABASE_PORT: 5432
     TEST_DATABASE_HOST: localhost
     TEST_DATABASE_USER: test-user
     TEST_DATABASE_PSWD: test-pswd
     TEST_DATABASE_NAME: test-db
     TEST_DATABASE_PORT: 5433
     S3_BUCKET_NAME: jobbergate-k8s-staging
     S3_ENDPOINT_URL: None
     ARMASEC_DOMAIN: localhost:9080/realms/master/protocol/openid-connect
     ARMASEC_USE_HTTPS: True
     ARMASEC_AUDIENCE: https://local.omnivector.solutions
     ARMASEC_DEBUG: True
     ARMASEC_ADMIN_DOMAIN: None
     ARMASEC_ADMIN_AUDIENCE: None
     ARMASEC_ADMIN_MATCH_KEY: None
     ARMASEC_ADMIN_MATCH_VALUE: None
     IDENTITY_CLAIMS_KEY: https://omnivector.solutions
     SENTRY_DSN: None
     SENTRY_SAMPLE_RATE: 1.0
     MAX_UPLOAD_FILE_SIZE: 104857600
     SENDGRID_FROM_EMAIL: None
     SENDGRID_API_KEY: None

The command can also produce the output as JSON if needed:

.. code-block:: console

   poetry run dev-tools show-env --json
   {"DEPLOY_ENV": "LOCAL", "LOG_LEVEL": "DEBUG", "DATABASE_HOST": "localhost", "DATABASE_USER": "compose-db-user", "DATABASE_PSWD": "compose-db-pswd", "DATABASE_NAME": "compose-db-name", "DATABASE_PORT": 5432, "TEST_DATABASE_HOST": "localhost", "TEST_DATABASE_USER": "test-user", "TEST_DATABASE_PSWD": "test-pswd", "TEST_DATABASE_NAME": "test-db", "TEST_DATABASE_PORT": 5433, "S3_BUCKET_NAME": "jobbergate-k8s-staging", "S3_ENDPOINT_URL": null, "ARMASEC_DOMAIN": "localhost:9080/realms/master/protocol/openid-connect", "ARMASEC_USE_HTTPS": true, "ARMASEC_AUDIENCE": "https://local.omnivector.solutions", "ARMASEC_DEBUG": true, "ARMASEC_ADMIN_DOMAIN": null, "ARMASEC_ADMIN_AUDIENCE": null, "ARMASEC_ADMIN_MATCH_KEY": null, "ARMASEC_ADMIN_MATCH_VALUE": null, "IDENTITY_CLAIMS_KEY": "https://omnivector.solutions", "SENTRY_DSN": null, "SENTRY_SAMPLE_RATE": 1.0, "MAX_UPLOAD_FILE_SIZE": 104857600, "SENDGRID_FROM_EMAIL": null, "SENDGRID_API_KEY": null}


The ``dev-server`` subcommand
-----------------------------

This command starts up a local development server for the Jobbergate API. It will
be created using the configuration set up in the environment settings.

To start the server, run:

.. code-block:: console

   poetry run dev-tools dev-server
   2022-09-07 16:15:05.830 | INFO     | dev_tools.dev_server:dev_server:50 - Waiting for the database
   2022-09-07 16:15:05.830 | DEBUG    | dev_tools.dev_server:_wait_for_db:23 - database url is: postgresql://compose-db-user:compose-db-pswd@localhost:5432/compose-db-name
   2022-09-07 16:15:05.830 | DEBUG    | dev_tools.dev_server:_wait_for_db:26 - Checking health of database at postgresql://compose-db-user:compose-db-pswd@localhost:5432/compose-db-name: Attempt #0
   INFO:     Will watch for changes in these directories: ['/home/dusktreader/git-repos/omnivector/jobbergate/jobbergate-api']
   INFO:     Uvicorn running on http://0.0.0.0:5000 (Press CTRL+C to quit)
   INFO:     Started reloader process [27314] using statreload
   2022-09-07 16:15:06.555 | INFO     | jobbergate_api.main:<module>:39 - Skipping Sentry
   INFO:     Started server process [27319]
   INFO:     Waiting for application startup.
   2022-09-07 16:15:06.587 | INFO     | jobbergate_api.main:init_logger:71 - Logging configured 📝 Level: DEBUG
   2022-09-07 16:15:06.587 | DEBUG    | jobbergate_api.main:init_database:79 - Initializing database
   INFO:     Application startup complete.


There are additional options that can control some of the details of the settings of the
dev server. These can be examined with the ``--help`` flag:

.. code-block:: console

   $ poetry run dev-tools dev-server --help
   Usage: dev-tools dev-server [OPTIONS]

     Start a development server locally.

   Options:
     --db-wait-count INTEGER   How many times to attempt a check  [default: 3]
     --db-wait-interval FLOAT  Seconds to wait between checks  [default: 5.0]
     --port INTEGER            The port where the server should listen  [default:
                               5000]
     --log-level TEXT          The level to log uvicorn output  [default: DEBUG]
     --help                    Show this message and exit.


Note the ``--db-wait-*`` flags. These are used to make the dev server wait for the
dev database to become available. These are mostly useful in the context of
``docker-compose``.

It should also be noted that a development uvicorn server will automatically reload the
app if the source files of the app change. This is very helpful for debugging behavior
in the app without having to manually stop and start the app after every source code
modification.


.. _alembic: https://alembic.sqlalchemy.org/en/latest/
.. _sqlalchemy: https://www.sqlalchemy.org/
