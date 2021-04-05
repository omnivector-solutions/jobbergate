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

### Database
It is needed to start a postgres instance, the fastest way is to use docker

For the tests to run:
```bash
docker run --name postgres-test -e POSTGRES_PASSWORD=password -d -p 5432:5432 postgres
```

And to run locally:
```bash
docker run --name postgres -e POSTGRES_PASSWORD=password -d -p 6432:5432 postgres
```

After the docker images are running, create the tables with:
```bash
make migrate
```

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
