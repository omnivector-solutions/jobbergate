# Jobbergate CLI Overview

The [Jobbergate CLI](https://github.com/omnivector-solutions/jobbergate/jobbergate-cli) offers an interactive
gateway to the functionalities of the Jobbergate API's. Users can utilize the CLI to manage resources and execute
various tasks.

The CLI operates under two primary modes:

 - **Resource Creation**: The CLI introduces `create` subcommands for every resource, allowing users to establish new
   instances.
 - **Resource Viewing**: With `list` and `get-one` subcommands available for each resource, users can inspect different
   detail levels about the resource entities stored in the database.

To ensure secure access, the Jobbergate CLI offers a sign-in mechanism to the Jobbergate API. Once authenticated,
users may use all the resources in Jobbergate that their account has been granted access to.


## Discovering Command details

You can start learning about the commands and usage of the Jobbergate CLI by starting with this command:

```shell

$ jobbergate --help
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
```

If you want to delve deeper and understand the usage of a specific subcommand, you can use the `--help` flag with that
particular subcommand. For example, to better understand the usage of the `job-scripts create` subcommand, you would
run:

```shell
$ jobbergate job-scripts create --help
```



## Logging In

The first thing you need to do with the Jobbergate CLI is to log in:

```shell
jobbergate login
```
Upon executing the command, a message will appear like:

```
╭───────────────────────────────────────────── Waiting for login ──────────────────────────────────────────────────────╮
│                                                                                                                      │
│   To complete login, please open the following link in a browser:                                                    │
│                                                                                                                      │
│     http://keycloak.local:8080/realms/jobbergate-local/device?user_code=BMVJ-NLZS                                    │
│                                                                                                                      │
│   Waiting up to 5.0 minutes for you to complete the process...                                                       │
│                                                                                                                      │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Waiting for web login... ━╺━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   3% 0:04:50
```

Next, you will need to:

 1. Open the provided link by either clicking on it (if your terminal supports it) or copy/paste it into a browser.
 2. Enter your login credentials
 3. Complete the sign in process
 4. Return to your terminal

You should see a message like:

```
╭──────────────────────────────────────────────── Logged in! ──────────────────────────────────────────────────────────╮
│                                                                                                                      │
│   User was logged in with email 'local-user@jobbergate.local'                                                        │
│                                                                                                                      │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```


## Checking the Auth Token

To get access to the auth token you acquired by logging in, run this command:

```shell
jobbergate show-token --plain
```
Executing this command will display the authentication token in a plain text format, without any additional characters
or formatting. This makes it easier for you to manually select and copy the token, especially in environments where
clipboard access might be restricted, such as when using docker-compose or an SSH connection.

Once the token is displayed, you can copy the token to your clipboard to use with API requests.

It's essential to treat this token with care, as it provides access to the Jobbergate system under your user account.
Ensure you don't share it with unauthorized individuals and avoid unintentionally exposing it in logs or scripts.



## Resource Commands

Now that you are logged in, you can interact with any of the three main Jobbergate resources. Most of the resources
provide the following sub-commands:

* **create**: Create a new instance of the resource
* **delete**: Delete an instance of the resource
* **get-one**: Fetch details about a single instance of the resource
* **list**: Fetch a listing of all the resources limited by filters
* **update**: Update an instance of the resource.

Details for each subcommand can be viewed by passing the `--help` flag to any of them.

Use the `--help` option to explore the CLI and disccover the usage and options for all the subcommands.


## Usability

To ensure that you can see the full output of the CLI, we recommend that you use a terminal in a maximized window.
