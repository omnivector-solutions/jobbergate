# Jobbergate Composed

_Jobbergate, Slurm, and Keycloak deployed to docker-compose._

By making a simple, local deployment of Jobbergate, this project provides:

- A test-bed for Jobbergate with minimal dependencies
- An example against which guides, tutorials, and other examples can operate
- A demonstration of how Jobbergate interacts with other components
- A reference for the environment variables and settings Jobbergate relies upon


> **Warning**
>
> The images and configuration found in this sub-project should _not_ be used in
> production environments. They are very specifically tailored for example use-
> cases where debuggging and access need to be simplified.


## Requirements

* [Docker Desktop with Docker Compose](https://www.docker.com/get-started/)


## Usage

To spin everything up using `docker-compose`, simply execute the following command:

```shell
docker-compose up --build
```


Then, you can begin executing commands via the `jobberate-cli` by running bash within
the container built for it:

```shell
docker-compose run jobbergate-cli bash
```


Once the bash shell in the container has started, you can start running jobbergate
commands:

```shell
jobbergate --help
```


Here's an example of Jobbergate CLI in action within a composed container:

[![Composed Demo](https://asciinema.org/a/AipfkeV2OiOMpM3yPwCSocJ6l.png)](https://asciinema.org/a/AipfkeV2OiOMpM3yPwCSocJ6l?autoplay=1)


Note that this setup creates a user automatically that can be used for exploring the
app or unit testing. The username is "local-user" with a password of "local".


## Usage Note

To use the login link provided in the terminal, you need to set up an alias for
keycloak (the identity & auth provider) in your operating system's hostfile.

Simply add this line to your hostfile:

```
127.0.0.1   keycloak.local
```


For Linux and OSX, this file is located at `/etc/hosts`.
For Windows, it is found at `c:\windows\system32\drivers\etc\hosts`


# License

* [MIT](LICENSE)


# Copyright

* Copyright (c) 2022 OmniVector Solutions <info@omnivector.solutions>
