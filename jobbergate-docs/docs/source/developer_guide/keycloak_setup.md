# Setting up Keycloak for Jobbergate

Jobbergate's security is provided by the [Armasec package](https://github.com/omnivector-solutions/armasec) which should
be compatible with any OIDC provider. However, the recommended provider is Keycloak.

In this guide, we outline the steps to integrate an existing Keycloak instance (version 19.0.2 as used in this example)
with Jobbergate to ensure a smooth user experience and enhanced security features.

Although this tutorial focuses on integrating Keycloak with a locally deployed instance of Jobbergate, such as one
housed in a Docker container via the `jobbergate-composed` sub-project, the procedures can be easily adapted to suit
deployments on single-node Keycloak clusters or other complex configurations.

## Create a new Realm

You have the option to utilize an existing realm for Jobbergate, but for a streamlined process, it's typically more
advantageous to create a new realm specifically for your Jobbergate deployment.

Once you're logged into the Keycloak interface, navigate and click the Add realm button, found beneath the Select realm
dropdown menu on the left-hand side.

For those using a local Jobbergate deployment, you should assign the Name as "jobbergate-local".

You'll also need to specify a Frontend URL. Avoid using "localhost" because a valid domain is required for the
redirection to function correctly. A suitable alternative is the .local special domain; this domain is ideal as it isn't
subject to reservation on any DNS. For instance, your full Frontend URL would be <http://keycloak.local:8080>.

The remaining realm settings can be left at their default configurations.

### Setup Hostfile

For the Keycloak admin UI to work correctly in a local deployment, it's essential to include the `keycloak.local` domain
in your system’s hostfile.

For users on Linux or OSX, you can find this file at `/etc/hosts`. Windows users can locate it at
`c:\windows\system32\drivers\etc\hosts`.

Editing this file requires administrative or sudo privileges.

Upon accessing the file, append the following line and save your changes:

```plain
127.0.0.1   keycloak.local
```

This step ensures that the `Frontend URL` resolves correctly, facilitating seamless navigation and operation.

## Create a new Client for the CLI

To facilitate login and JWT authentication for the Jobbergate CLI, it's essential to allocate a dedicated client.

Begin by navigating to the `Clients` section, found on the left sidebar, and then proceed to click on the `Create`
button located on the right.

When adjusting the `Client Protocol` settings, select the `openid-connect` option. For the `Client ID` setting, which
choosing an easy to identify name like "jobbergate-cli" is best even though this field can be any unique string.

To ensure the CLI can utilize this client for login purposes, it's vital to activate the `OAuth 2.0 Device Authorization
Grant` option.

If you're working with a local deployment, simply input "\*" in the `Valid Redirect URIs` section.

### Add Roles

Next, we need to add the needed roles for Jobbergate endpoints. These represent the fine-grained permissions that
are checked for each request to make sure that the user has permission to fulfill the request.

Click the `Roles` tab at the top, and then click on `Add Role` on the right.

Add the following roles:

| Name                            | Description                               |
|---------------------------------|-------------------------------------------|
| jobbergate:job-templates:edit   | Allow to view job templates               |
| jobbergate:job-templates:view   | Allow to view job templates               |
| jobbergate:job-scripts:edit     | Allow to edit job scripts                 |
| jobbergate:job-scripts:view     | Allow to view job scripts                 |
| jobbergate:job-submissions:edit | Allow to edit job submissions             |
| jobbergate:job-submissions:view | Allow to view job submissions             |

### Add Mappers

Jobbergate requires two claims that are not available by default. We will add them to the JWTs with Mappers.

Click the `Mappers`  tab at the top, and then click the `Create` button to add a new Mapper.

#### Audience

First, we need to add an "audience" mapper. Select "audience" for the `Name` field. Next, select "Audience" for the
`Mapper Type`.  The `Included Custom Audience` value may be whatever you like. The local deploy, by default, uses
<https://apis.omnivector.solutions>. Make sure to enable the `Add to ID token` setting.

#### Permissions

The `Armasec` package expects to find "permissions" in a claim at the root
of the JWT payload. To facilitate this, we need to add a mapper that will copy the permissions to the correct place in
the JWT. We will call the new mapper our "permissions" mapper.

Enter "Permissions" under the `Name` field. Next, select "User Client Role" as the `Mapper Type`.
Select "jobbergatel-cli" for the `Client ID`. The `Token Claim Name` *must* have the value "permissions". The
`Claim JSON Type` field must be "String".

## Create a new Client for the Agent

The Jobbergate Agent also requires its own client.

Again, click the `Clients` section on the left navigation bar, and then click the `Create` button on the right.

For the `Client Protocol` setting, choose the `openid-connect` protocol. The `Client ID` setting will be used to match
jobs to the cluster they should be submitted to. So use the cluster name for this setting. For a local deployment, the
`Client ID` should be "local-slurm".

On the `Settings` tab, set `Access Type` to `confidential` and enter "\*" for the `Valid Redirect URIs`. Scroll down and
click on the `Save` button.

### Add Roles

Click on the `Roles` tab, and click the `Add Role` button. Add all the following roles as above:

| Name                            | Description                               |
|---------------------------------|-------------------------------------------|
| jobbergate:job-templates:edit   | Allow to view Jobbergate applications     |
| jobbergate:job-templates:view   | Allow to view applications                |
| jobbergate:job-scripts:edit     | Allow to edit job scripts                 |
| jobbergate:job-scripts:view     | Allow to view job scripts                 |
| jobbergate:job-submissions:edit | Allow to edit job submissions             |
| jobbergate:job-submissions:view | Allow to view job submissions             |

### Add Mappers

Like the CLI client, the Agent's client also requires the "Audience" and "Permissions" mappers.

Click the `Mappers`  tab at the top, and then click the `Create` button to add a new Mapper.

#### Audience

First, we need to add an "audience" mapper. Select "audience" for the `Name` field. Next, select "Audience" for the
`Mapper Type`.  The `Included Custom Audience` value may be whatever you like. The local deploy, by default, uses
"<https://apis.omnivector.solutions>". Make sure to enable the `Add to ID token` setting.

#### Permissions

Next, add a "permissions" mapper. The `Armasec` package expects to find a "permissions" claims under a claim at the root
of the JWT payload. Enter "Permissions" under the `Name` field. Next, select "User Client Role" as the `Mapper Type`.
Select "jobbergatel-cli" for the `Client ID`. The `Token Claim Name` *must* have the value "permissions". The
`Claim JSON Type` field must be "String".

### Add Service Account Roles

To add the correct roles to the tokens issued for the Agent's client, we need to add some "Service Account Roles".

Click the `Service Account Roles` tab. Then, from the `Client Roles` drop-down, select the `local-slurm` client. Select
all of the Jobbergate roles created above and then click the `Add selected` button.

## Create User(s)

You will need to create some users that can use Jobbergate. These users will be able to sign-in through the Jobbergate
CLI. Each user must have a unique email address. Other than that, no special settings are needed.

To add a user, click `Users` on the left nav bar. Next, click the `Add user` button on the right.

Use the following settings, and then click the `Save` button.

| Username    | local-user                  |
| Email       | local-user@jobbergate.local |
| First Name  | Local                       |
| Last Name   | User                        |

After you have created the user, edit it by clicking on it in the list. You may need to click on the `View all users`
button to see it.

Click the `Credentials` tab at the top. Enter "local" for the `Password` and `Password Confirmation` field. Turn the
`Temporary` setting to `OFF`, and click `Reset Password`. Click the `Set password` verification button.

Next, click the `Role Mappings` tab at the top. Select the `jobbergate-local` entry in the `Client Roles` drop-down.
Select all of the roles for jobbergate added above and click `Add selected` to add them to the user.

## Conclusion

Your Keycloak instance is now prepared for use by Jobbergate! For additional information on configuring Keycloak and
Armasec, consult documentation at:

- <https://www.keycloak.org/documentation>
- <https://omnivector-solutions.github.io/armasec/>
