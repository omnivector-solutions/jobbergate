================
 Jobbergate CLI
================

Jobbergate CLI client



Usage
-----

.. code-block:: console

    jobbergate --help

.. note::

   It is possible to use raw sbatch parameters in create-job-script

   Use the `--sbatch-params` multiple times to use as many parameters as needed in the
   following format ``--sbatch-params='-N 10'`` or
   ``--sbatch-params='--comment=some_comment'``


Release Process & Criteria
--------------------------

Run automated tests
...................

Run:

.. code-block:: console

   make qa

This will run unit tests and linter.


Integration testing
...................

You should verify that each of the functions of the CLI work as expected.

First, prepare your environment:

.. code-block:: console

   JOBBERGATE_API_ENDPOINT=https://jobbergate-api-staging.omnivector.solutions

Then, run the following tests:
- ``jobbergate --version`` (confirm new version number)
- ``create-application``
- ``create-job-script``
- ``create-job-submission``
- ``update-application``
- ``update-job-script``
- ``update-job-submission``
- ``list-job-submissions``

(FIXME: most of the above should be covered by automated system tests.)


Create a release
................

First, decided on the scope of the release:
* major - Significant new features added and/or there are breaking changes to the app
* minor - New features have been added or major flaws repaired
* patch - Minor flaws were repaired or trivial features were added

Next, make the release with the selected scope:

.. code-block:: console

   make release-<scope>

So, for example, to create a minor release, you would run:

.. code-block:: console

   make relase-minor

You must have permission to push commits to the main branch to create a release.

If the release script fails, contact a maintainer to debug and fix the release.


License
-------
* `MIT <LICENSE>`_


Copyright
---------
* Copyright (c) 2020-2021 OmniVector Solutions <info@omnivector.solutions>
