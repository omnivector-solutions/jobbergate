============
 Jobbergate
============

Jobbergate is a system used to manage reusable applications that can generate specific scripts that
may be sumbitted via Slurm for execution on a cluster.

There are two core apps that comprise Jobbergate. These are

* ``jobbergate-cli``
* ``jobbergate-api``

There are 3 main resources that both apps interact with. These are:

* ``Application``
* ``JobScript``
* ``JobSubmission``


Resources
=========

The resources are represented in the app code and stored in the database with which they
interact.


Application
-----------

This is the base for the ``JobScript`` and ``JobSubmission`` resources. ``Applications`` provide
re-usable templates that maybe be rendered into ``JobScript`` instances. An ``Application`` consists
of an application folder that contains:

* jobbergate.py:   the application source code (for describing how to gather configuration options)
* jobbergate.yaml: the application config and jobbergate config
* templates:       a set of template files that will be rendered with the supplied config


JobScript
---------

This is the main resource. It describes the actual job that will run in the clusters.
The base to create a ``JobScript`` is the ``Application``. A single application to generate many
``JobScripts`` that vary by the parameters passed at creation time.


JobSubmission
-------------

This is a result of a submitting a ``JobScript`` to the system. It is linked to it by its ID and also
has the ``slurm job id`` for the running job.


Apps
====

Both Jobbergate apps are Python applications, though one is a command-line-interface (CLI) and one
is a RESTful API.


jobbergate-api
--------------

The `jobbergate-api <jobbergate-api/>`_ is a RESTful API that serves as the back-end for the system.
It is interacted with via the CLI, though requests can be dispatched to it from any other web
application.

.. todo::

   Fix the link below after project migration is complete

There jobbergate-api offers `interactive documentation via swagger
<https://jobbergateapi2-staging.omnivector.solutions/docs>`_

Requests to the API must be accompanied by a JWT issued by a Auth0.


jobbergate-cli
--------------

The `jobbergate-cli <https://github.com/omnivector-solutions/jobbergate-cli>`_ provides interactive
access to Jobbergate resources via a CLI. Its commands provide access to the CRUD operations for
the reosurces ``Application``, ``JobScript`` and ``JobSubmission``. It communicates directly with
``jobbergate-api`` using HTTP requests and is secured by a long-lived Auth0 access token.
