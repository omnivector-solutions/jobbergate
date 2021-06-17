# jobbergate-api-fastapi

## Permissions
We are using the [fastapi_permissions](https://github.com/holgi/fastapi-permissions) to manage the
permissions.

The User model has the `principals` field, that holds its permissions roles (e.g. `Authenticated` or
`role:admin`). Every user that is authenticated has the `Authenticated` role automatically. It is important
to note that the `principals` field is a String field in the database, and each entry is separated by `|`.

Every other resource has the `<resource>Permission` (e.g. `ApplicationPermission`) that holds the ACL for that resource.
For example if we want to all the authenticated users to view the `applications`, we need to create the `view`
permission, it is done like this:

```bash
POST /permissions/?permission_query=application data={"acl": "Allow|Authenticated|view"}
```

And each line in the `<resource>_permissions_table` is in this format: (action, principal, permission), but
are a String field in the database, for example: `Allow|role:admin|view` and `Deny|Authenticated|delete`.
It is checked by the following RegEx: `r"^(Allow|Deny)\|(role:\w+|Authenticated)\|\w+$"`.

We have currently the following permissions: `view`, `create`, `update`, `delete`.

## Note
Only the User with `is_superuser=True` can modify the permissions.

## Local development

### Install poetry
The easier way to develop this project is to use poetry, to that, use the instructions [here](https://github.com/python-poetry/poetry#installation)

### Install the dependencies
```bash
make install
```

### Create the .env
```bash
cp default.env .env
```
Then generate the SECRET_KEY with:
```bash
openssl rand -hex 32
```
And add it to the .env

### Create a super user
To test locally first you need to create a super user to authenticate with and make the requests
```bash
make createsuperuser
```

### Test the project
```bash
make test
```

### Run locally
The following command will start the application, and it is possible to try it [here](http://localhost:8000/docs)
```bash
make run
```
