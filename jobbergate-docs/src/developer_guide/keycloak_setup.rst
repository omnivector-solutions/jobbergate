====================================
 Setting up Keycloak for Jobbergate
====================================

Though Jobbergate should be compatible with any OIDC provider (through the `Armasec package
<https://github.com/omnivector-solutions/armasec>`_), the recommended provider is Keycloak.

This document describes the procedure for setting up an already deployed Keycloak instance to work with Jobbergate.

The version of Keycloak used for this guide is `19.0.2`.

The examples provided here describe how to set it up for a local deployment (for example, one deployed with Docker).
However, the instructions should be easily extensible for any deployment.


Create a new Realm
------------------

It is possible to configure an existing realm for Jobbergate, however, it may be most convenient to start with a new
realm set aside for your Jobbergate deployment.

After logging in to the keycloak frontend, click the `Add realm` button under the `Selet realm` drop-down on the left.

For locally deployed Jobbergate, set `Name` to "jobbergate-local".

The realm will require a `Frontend URL`. It is not convenient to use "localhost" for this URL because the redirect
requires a valid domain. The `.local` special domain is perfect for this, because it cannot be used as a reserved name
on any DNS. The full `Frontend URL` value should be "http://keycloak.local:8080".

Leave all the rest of the realm settings as defaults.


Hostfile Note
.............

To allow the `Frontend URL` to work, you need to add the `keycloak.local` domain to your hostfile.

For Linux and OSX, this file is located at ``/etc/hosts``.
For Windows, it is found at ``c:\windows\system32\drivers\etc\hosts``

(You will need to be admin/sudo to edit this file)

Once you have located the file, add this line to it and save::

   127.0.0.1   keycloak.local


Create a new Client for the CLI
-------------------------------

Next, there needs to be a client set aside for the Jobbergate CLI to use to log in and sign JWT for auth.

Click the `Clients` section on the left navigation bar, and then click the `Create` button on the right.

For the `Client Protocol` setting, choose the `openid-connect` protocol. The `Client ID` setting is only important for
finding it later; "jobbergate-cli" is a convenient `Client ID`.

To allow the CLI to use this client for login, you must enable `OAuth 2.0 Device Authorization Grant`.

For a local deployment just add "*" under `Valid Redirect URIs`.


Add Roles
.........

Next, we need to add the needed roles for Jobbergate endpoints. These represent the fine-grained permissions that
are checked for each request to make sure that the user has permission to fulfill the request.

Click the `Roles` tab at the top, and then click on `Add Role` on the right.

Add the following roles:

+---------------------------------+-------------------------------------------+
| Name                            | Description                               |
+=================================+===========================================+
| jobbergate:applications:edit    | Allow to view Jobbergate applications     |
+---------------------------------+-------------------------------------------+
| jobbergate:applications:view    | Allow to view applications                |
+---------------------------------+-------------------------------------------+
| jobbergate:job-scripts:edit     | Allow to edit job scripts                 |
+---------------------------------+-------------------------------------------+
| jobbergate:job-scripts:view     | Allow to view job scripts                 |
+---------------------------------+-------------------------------------------+
| jobbergate:job-submissions:edit | Allow to edit job submissions             |
+---------------------------------+-------------------------------------------+
| jobbergate:job-submissions:view | Allow to view job submissions             |
+---------------------------------+-------------------------------------------+
| license-manager:booking:edit    | Allow to edit bookings                    |
+---------------------------------+-------------------------------------------+
| license-manager:booking:view    | Allow to view bookings                    |
+---------------------------------+-------------------------------------------+


Add Mappers
...........

Jobbergate requires two claims that are not available by default. We will add them to the JWTs with Mappers.

Click the `Mappers`  tab at the top, and then click the `Create` button to add a new Mapper.

Audience
********

First, we need to add an "audience" mapper. Select "audience" for the `Name` field. Next, select "Audience" for the
`Mapper Type`.  The `Included Custom Audience` value may be whatever you like. The local deploy, by default, uses
"https://apis.omnivector.solutions". Make sure to enable the `Add to ID token` setting.

Permissions
***********

Next, add a "permissions" mapper. The `Armasec` package expects to find a "permissions" claims under a claim at the root
of the JWT payload. Enter "Permissions" under the `Name` field. Next, select "User Client Role" as the `Mapper Type`.
Select "jobbergatel-cli" for the `Client ID`. The `Token Claim Name` *must* have the value "permissions". The
`Claim JSON Type` field must be "String".


Create a new Client for the Agent
---------------------------------

The Jobbergate Agent will also need a client.

Again, click the `Clients` section on the left navigation bar, and then click the `Create` button on the right.

For the `Client Protocol` setting, choose the `openid-connect` protocol. The `Client ID` setting will be used to match
jobs created for the agent to submit to Slurm, so use the cluster name for this setting. For a local deployment, the
`Client ID` should be "local-slurm".

On the `Settings` tab, set `Access Type` to `confidential` and enter "*" for the `Valid Redirect URIs`. Scroll down and
click on the `Save` button.

Add Roles
.........

Click on the `Roles` tab, and click the `Add Role` button. Add all the following roles as above:

+---------------------------------+-------------------------------------------+
| Name                            | Description                               |
+=================================+===========================================+
| jobbergate:applications:edit    | Allow to view Jobbergate applications     |
+---------------------------------+-------------------------------------------+
| jobbergate:applications:view    | Allow to view applications                |
+---------------------------------+-------------------------------------------+
| jobbergate:job-scripts:edit     | Allow to edit job scripts                 |
+---------------------------------+-------------------------------------------+
| jobbergate:job-scripts:view     | Allow to view job scripts                 |
+---------------------------------+-------------------------------------------+
| jobbergate:job-submissions:edit | Allow to edit job submissions             |
+---------------------------------+-------------------------------------------+
| jobbergate:job-submissions:view | Allow to view job submissions             |
+---------------------------------+-------------------------------------------+
| license-manager:booking:edit    | Allow to edit bookings                    |
+---------------------------------+-------------------------------------------+
| license-manager:booking:view    | Allow to view bookings                    |
+---------------------------------+-------------------------------------------+


Add Mappers
...........

Like the CLI client, the Agent's client also requires the "Audience" and "Permissions" mappers.

Click the `Mappers`  tab at the top, and then click the `Create` button to add a new Mapper.


Audience
********

First, we need to add an "audience" mapper. Select "audience" for the `Name` field. Next, select "Audience" for the
`Mapper Type`.  The `Included Custom Audience` value may be whatever you like. The local deploy, by default, uses
"https://apis.omnivector.solutions". Make sure to enable the `Add to ID token` setting.


Permissions
***********

Next, add a "permissions" mapper. The `Armasec` package expects to find a "permissions" claims under a claim at the root
of the JWT payload. Enter "Permissions" under the `Name` field. Next, select "User Client Role" as the `Mapper Type`.
Select "jobbergatel-cli" for the `Client ID`. The `Token Claim Name` *must* have the value "permissions". The
`Claim JSON Type` field must be "String".


Add Service Account Roles
.........................

To add the correct roles to the tokens issued for the Agent's client, we need to add some "Service Account Roles".

Click the `Service Account Roles` tab. Then, from the `Client Roles` drop-down, select the `local-slurm` client. Select
all of the Jobbergate roles created above and then click the `Add selected` button.


Create User(s)
--------------

You will need to create some users that can use Jobbergate. These users will be able to sign-in through the Jobbergate
CLI. Each user must have a unique email address. Other than that, no special settings are needed.

To add a user, click `Users` on the left nav bar. Next, click the `Add user` button on the right.

Use the following settings, and then click the `Save` button.

+-------------+-----------------------------+
| Username    | local-user                  |
+-------------+-----------------------------+
| Email       | local-user@jobbergate.local |
+-------------+-----------------------------+
| First Name  | Local                       |
+-------------+-----------------------------+
| Last Name   | User                        |
+-------------+-----------------------------+

After you have created the user, edit it by clicking on it in the list. You may need to click on the `View all users`
button to see it.

Click the `Credentials` tab at the top. Enter "local" for the `Password` and `Password Confirmation` field. Turn the
`Temporary` setting to `OFF`, and click `Reset Password`. Click the `Set password` verification button.

Next, click the `Role Mappings` tab at the top. Select the `jobbergate-local` entry in the `Client Roles` drop-down.
Select all of the roles for jobbergate added above and click `Add selected` to add them to the user.


Conclusion
----------

Your Keycloak instance is now prepared for use by Jobbergate! For additional information on configuring Keycloak and
Armasec, consult documentation at:

* https://www.keycloak.org/documentation
* https://omnivector-solutions.github.io/armasec/
