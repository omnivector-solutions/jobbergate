# Jobbergate API

The Jobbergate API provides a RESTful interface over the Jobbergate data and is used
by both the `jobbergate-agent` and the `jobbergate-cli` to view and manage the
Jobbergate resources.

Jobbergate API is a Python project implemented with
[FastAPI](https://fastapi.tiangolo.com/). Its dependencies and environment are
managed by [Poetry](https://python-poetry.org/).

It integrates with an OIDC server to provide identity and auth for its endpoints.

See also:

* [jobbergate-cli](https://github.com/omnivector-solutions/jobbergate/jobbergate-cli)

## License

* [MIT](./LICENSE)

## Copyright

* Copyright (c) 2020 OmniVector Solutions <info@omnivector.solutions>
