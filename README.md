# jobbergate-api-fastapi

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

The following confuration settings are needed for auth in jobbergate:

* ARMASEC_DOMAIN
  This should be the domain name for the OIDC provider API
* ARMASEC_AUDIENCE
  This field is required when using Auth0. It should match the API Audience
* ARMASEC_DEBUG
  If this is enabled, extra logging and some stack traces that are usually obscured will be visible. This
  should ONLY be used in a non-production environment


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
