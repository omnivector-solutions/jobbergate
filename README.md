# jobbergate-api-fastapi

## Permissions
TODO: Update this with a description of how permissions are handled

## Local development

### Install poetry
The easier way to develop this project is to use poetry, to that, use the instructions
[here](https://github.com/python-poetry/poetry#installation)

### Install the dependencies
```bash
make install
```

### Create the .env
```bash
cp default.env .env
```
To use auth0 tokens, you will need to retrieve the secret for the app from Auth0
TODO: Talk about NEVER copying secrets like this onto local file system. Use docker
      secrets or environment variables

### Test the project
```bash
make test
```

### Run locally
TODO: Refer to using docker-compose in the `jobbergate-composed` project

The following command will start the application, and it is possible to try it
[here](http://localhost:8000/docs)
```bash
make run
```
