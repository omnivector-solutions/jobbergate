# jobbergate-api-fastapi

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
