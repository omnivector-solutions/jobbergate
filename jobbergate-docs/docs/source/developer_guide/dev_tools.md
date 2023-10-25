# API Dev Tools

The Jobbergate API sub-project is equipped with a few tools designed to assist with
some everyday development tasks. These can help streamline the process of setting up and
interacting with the API.

The dev-tools are shipped as a CLI program that can be invoked via Poetry within the
project. All of the commands will operate within the virtual environment set up by
Poetry.

## Invoking `dev-tools`

To invoke the dev tools, you must execute the commands from the home directory for the
`jobbergate-api`. To see some information about the `dev-tools`, execute:

```console
poetry run dev-tools --help
```

This will provide some help output that shows what options and sub-commands are
available:

```plain
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
```

The `--help` option is available for all of the subcommands provided in `dev-tools`.

## The `db` subcommand

There are a few convenience methods in the `dev-tools` for interacting with Jobbergate
API's PostgreSQL database. These tools are found in the `db` subcommand. To see more
info about this sub-command, run:

```shell
poetry run dev-tools db --help
```

### The `login` subcommand

This command allows you to log in to the database that your Jobbergate API is configured
to connect with. It allows you to login to databases, regardless of whether they are
locally hosted via Docker or situated on a remote PostgreSQL server. this ensures
seamless access to any database that the Jobbergate API is configured to connect with.

To log in to the database, execute this command:

```shell
poetry run dev-tools db login
```

The command will show some debug output including the URL of the database to which it is
connecting and will then show a REPL connection to the database:

```plain
2022-09-07 15:52:02.089 | DEBUG    | dev_tools.db:login:26 - Logging into database: postgresql://compose-db-user:compose-db-pswd@localhost:5432/compose-db-name
Server: PostgreSQL 14.1 (Debian 14.1-1.pgdg110+1)
Version: 3.4.1
Home: http://pgcli.com
compose-db-name>
```

### The `migrate` subcommand

This command uses [alembic](https://alembic.sqlalchemy.org/en/latest/) to generate a
migration script to bring the current database (described by the environment) up to date
with the [SQLAlchemy](https://www.sqlalchemy.org/) models specified in the Jobbergate
API source code.

To invoke the migration script generation, execute:

```shell
poetry run dev-tools db migrate --message="An example migration"
```

Some logging info will be produced, including the location of the new migration script:

```plain
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
```

The generated migration should *always* be reviewed before it is committed to the
repository.

It is also possible to produce a blank migration if you need to execute some raw SQL or
write an Alembic script by hand. Just pass the `--blank` parameter on the command
line:

```shell
poetry run dev-tools db migrate --blank --message="A blank migration"
```

### The `upgrade` subcommand

This subcommand is used to apply a database migration to the database that the
Jobbergate API is configured to connect with.

By default, it will apply all the migrations that have not yet been applied to the
database.

To apply the migrations, execute the command:

```shell
poetry run dev-tools db upgrade
```

It will produce some logging output that shows what migrations were applied:

```plain
2022-09-07 16:05:46.315 | DEBUG    | dev_tools.db:upgrade:89 - Upgrading database...
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade d22da0741b7f -> c275de463a90, An example migration
```

If you wish to only upgrade the database *to* a specific migration, you can pass that
migration's id to the `--target` param.

## The `show-env` subcommand

This command will show how the Jobbergate API is configured through its environment
settings. To see the environment, execute this command:

```shell
poetry run dev-tools show-env
```

The output that the command produces will look something like:

```plain
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
```

The command can also produce the output as JSON if needed by passing the `--json` flag:

```shell
poetry run dev-tools show-env --json
```

The JSON output will look something like:

```json
{"DEPLOY_ENV": "LOCAL", "LOG_LEVEL": "DEBUG", "DATABASE_HOST": "localhost", "DATABASE_USER": "compose-db-user", "DATABASE_PSWD": "compose-db-pswd", "DATABASE_NAME": "compose-db-name", "DATABASE_PORT": 5432, "TEST_DATABASE_HOST": "localhost", "TEST_DATABASE_USER": "test-user", "TEST_DATABASE_PSWD": "test-pswd", "TEST_DATABASE_NAME": "test-db", "TEST_DATABASE_PORT": 5433, "S3_BUCKET_NAME": "jobbergate-k8s-staging", "S3_ENDPOINT_URL": null, "ARMASEC_DOMAIN": "localhost:9080/realms/master/protocol/openid-connect", "ARMASEC_USE_HTTPS": true, "ARMASEC_AUDIENCE": "https://local.omnivector.solutions", "ARMASEC_DEBUG": true, "ARMASEC_ADMIN_DOMAIN": null, "ARMASEC_ADMIN_AUDIENCE": null, "ARMASEC_ADMIN_MATCH_KEY": null, "ARMASEC_ADMIN_MATCH_VALUE": null, "IDENTITY_CLAIMS_KEY": "https://omnivector.solutions", "SENTRY_DSN": null, "SENTRY_SAMPLE_RATE": 1.0, "MAX_UPLOAD_FILE_SIZE": 104857600, "SENDGRID_FROM_EMAIL": null, "SENDGRID_API_KEY": null}
```

## The `dev-server` subcommand

This command starts up a local development server for the Jobbergate API. It will
be created using the configuration set up in the environment settings. This command is especially useful if
you want to run the API locally but connect to remote services such as a database and s3 hosted on AWS.

To start the server, run:

```shell
poetry run dev-tools dev-server
```

The command will produce some logging output that looks like this:

```plain
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
```

There are additional options that can control some of the details of the settings of the
dev server. These can be examined with the `--help` flag:

```shell
poetry run dev-tools dev-server --help
```

The dev server options will be printed like:

```plain
Usage: dev-tools dev-server [OPTIONS]

  Start a development server locally.

Options:
  --db-wait-count INTEGER   How many times to attempt a check  [default: 3]
  --db-wait-interval FLOAT  Seconds to wait between checks  [default: 5.0]
  --port INTEGER            The port where the server should listen  [default:
                            5000]
  --log-level TEXT          The level to log uvicorn output  [default: DEBUG]
  --help                    Show this message and exit.
```

The `--db-wait-*` flags are used to make the dev server wait for the dev database to
become available. These are mostly useful in the context of `docker-compose`.

It should also be noted that a development uvicorn server will automatically reload the
app if the source files of the app change. This is very helpful for debugging behavior
in the app without having to manually stop and start the app after every source code
modification.
