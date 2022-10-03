.. raw:: html

   <p align="center">
     <img
       src="https://img.shields.io/github/workflow/status/omnivector-solutions/jobbergate/Test/main?label=main-build&logo=github&style=plastic"
       alt="main build"
     />
     <img
       src="https://img.shields.io/github/contributors/omnivector-solutions/jobbergate?logo=github&style=plastic"
       alt="github contributors"
     />
   </p>
   <p align="center">
     <img
       src="https://img.shields.io/pypi/pyversions/jobbergate-api?label=python-versions&logo=python&style=plastic"
       alt="python versions"
     />
     <img
       src="https://img.shields.io/pypi/v/jobbergate-api?label=pypi-version&logo=python&style=plastic"
       alt="pypi version"
     />
     <img
       src="https://img.shields.io/pypi/l/jobbergate-api?style=plastic"
       alt="license"
     />
   </p>

   <p align="center">
     <img
       src="https://github.com/omnivector-solutions/jobbergate/blob/main/jobbergate-docs/src/images/logo.png?raw=true"
       alt="Logo" width="80" height="80"
     />
   </p>
   <p align="center"><i>An Omnivector Solutions initiative</i></p>


================
 Jobbergate API
================


The Jobbergate API provides a RESTful interface over the Jobbergate data and is used
by both the ``jobbergate-agent`` and the ``jobbergate-cli`` to view and manage the
Jobbergate resources.

Jobbergate API is a Python project implemented with
`FastAPI <https://fastapi.tiangolo.com/>`_. Its dependencies and environment are
managed by `Poetry <https://python-poetry.org/>`_.

It integrates with an OIDC server to provide identity and auth for its endpoints.

See also:

* `jobbergate-cli <https://github.com/omnivector-solutions/jobbergate/jobbergate-cli>`_

License
-------
* `MIT <LICENSE>`_


Copyright
---------
* Copyright (c) 2020 OmniVector Solutions <info@omnivector.solutions>
