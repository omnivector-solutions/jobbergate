=========================
 Quality Assurance Tools
=========================

Jobbergate makes use of quality control tools in all three of its major components (API,
CLI, and Agent). The tools are invoked in the same way in each of the subprojects, and
may be invoked *en masse* from the root Jobbergate directory.

  
Running Unit Tests
------------------

The main subprojects each make use of `pytest`_ to apply unit testing. The unit tests
for each subproject are contained in a subdirectory named ``tests/``.

To invoke all of the unit tests for a subproject, you may use ``make``:

.. code-block:: console

   make test


The test suite will then begin running. For the API, this process takes a few minutes.
The others only take a few seconds. The status of the tests will be logged to the
console as well as a coverage report for the unit tests::

   ================================================================== test session starts ===================================================================
   platform linux -- Python 3.8.12, pytest-6.2.5, py-1.11.0, pluggy-1.0.0
   Using --random-order-bucket=module
   Using --random-order-seed=650699

   rootdir: /home/dusktreader/git-repos/omnivector/jobbergate/jobbergate-api, configfile: pyproject.toml, testpaths: jobbergate_api/tests
   plugins: asyncio-0.12.0, random-order-1.0.4, respx-0.17.1, env-0.6.2, armasec-0.11.0, freezegun-0.4.2, cov-2.12.1, anyio-3.5.0
   collecting ... 2022-09-07 16:31:37.548 | INFO     | jobbergate_api.main:<module>:39 - Skipping Sentry
   collected 158 items

   jobbergate_api/tests/apps/job_scripts/test_routers.py ........................                                                                     [ 15%]
   jobbergate_api/tests/apps/applications/test_schemas.py ....                                                                                        [ 17%]
   jobbergate_api/tests/test_file_validation.py ...........                                                                                           [ 24%]
   jobbergate_api/tests/test_email_notification.py .......                                                                                            [ 29%]
   jobbergate_api/tests/apps/applications/test_application_files.py .........                                                                         [ 34%]
   jobbergate_api/tests/apps/job_submissions/test_routers.py .................................                                                        [ 55%]
   jobbergate_api/tests/apps/job_scripts/test_job_script_files.py .........                                                                           [ 61%]
   jobbergate_api/tests/apps/test_main.py .                                                                                                           [ 62%]
   jobbergate_api/tests/test_meta_mapper.py ...                                                                                                       [ 63%]
   jobbergate_api/tests/test_s3_manager.py ...                                                                                                        [ 65%]
   jobbergate_api/tests/test_config.py ................                                                                                               [ 75%]
   jobbergate_api/tests/test_pagination.py ........                                                                                                   [ 81%]
   jobbergate_api/tests/test_storage.py ..                                                                                                            [ 82%]
   jobbergate_api/tests/test_security.py ...                                                                                                          [ 84%]
   jobbergate_api/tests/apps/applications/test_routers.py .........................                                                                   [100%]

   ==================================================================== warnings summary ====================================================================
   jobbergate_api/tests/conftest.py:53
     /home/dusktreader/git-repos/omnivector/jobbergate/jobbergate-api/jobbergate_api/tests/conftest.py:53: PytestUnknownMarkWarning: Unknown pytest.mark.enforce_empty_database - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/mark.html
       @pytest.mark.enforce_empty_database()

   jobbergate_api/tests/apps/job_scripts/test_routers.py: 37 warnings
   jobbergate_api/tests/apps/job_submissions/test_routers.py: 40 warnings
   jobbergate_api/tests/test_pagination.py: 10 warnings
   jobbergate_api/tests/apps/applications/test_routers.py: 42 warnings
     /home/dusktreader/.cache/pypoetry/virtualenvs/jobbergate-api-zc2JKxO9-py3.8/lib/python3.8/site-packages/databases/backends/postgres.py:114: DeprecationWarning: The `Row.keys()` method is deprecated to mimic SQLAlchemy behaviour, use `Row._mapping.keys()` instead.
       warnings.warn(

   -- Docs: https://docs.pytest.org/en/stable/warnings.html

   ---------- coverage: platform linux, python 3.8.12-final-0 -----------
   Name                                                               Stmts   Miss  Cover   Missing
   ------------------------------------------------------------------------------------------------
   jobbergate_api/__init__.py                                             0      0   100%
   jobbergate_api/apps/__init__.py                                        0      0   100%
   jobbergate_api/apps/applications/__init__.py                           0      0   100%
   jobbergate_api/apps/applications/application_files.py                 77      0   100%
   jobbergate_api/apps/applications/models.py                             7      0   100%
   jobbergate_api/apps/applications/routers.py                          136     14    90%   64-66, 129-131, 136-137, 210-212, 331-332, 341
   jobbergate_api/apps/applications/schemas.py                           66      0   100%
   jobbergate_api/apps/job_scripts/__init__.py                            0      0   100%
   jobbergate_api/apps/job_scripts/job_script_files.py                  121      4    97%   67, 80-81, 270
   jobbergate_api/apps/job_scripts/models.py                              7      0   100%
   jobbergate_api/apps/job_scripts/routers.py                           132     11    92%   98-100, 108-109, 235-237, 267-269, 301
   jobbergate_api/apps/job_scripts/schemas.py                            38      0   100%
   jobbergate_api/apps/job_submissions/__init__.py                        0      0   100%
   jobbergate_api/apps/job_submissions/constants.py                      11      0   100%
   jobbergate_api/apps/job_submissions/models.py                          8      0   100%
   jobbergate_api/apps/job_submissions/routers.py                       186     12    94%   101-103, 260-262, 382, 395-400, 406, 449
   jobbergate_api/apps/job_submissions/schemas.py                        51      0   100%
   jobbergate_api/apps/permissions.py                                     8      0   100%
   jobbergate_api/config.py                                              58      1    98%   102
   jobbergate_api/email_notification.py                                  28      0   100%
   jobbergate_api/file_validation.py                                    102      6    94%   36-56, 111, 175
   jobbergate_api/main.py                                                47      4    91%   31-37, 94
   jobbergate_api/meta_mapper.py                                         24      1    96%   104
   jobbergate_api/metadata.py                                             2      0   100%
   jobbergate_api/pagination.py                                          31      0   100%
   jobbergate_api/s3_manager.py                                          14      0   100%
   jobbergate_api/security.py                                            22      0   100%
   jobbergate_api/storage.py                                             52      1    98%   128
   jobbergate_api/tests/__init__.py                                       0      0   100%
   jobbergate_api/tests/apps/__init__.py                                  0      0   100%
   jobbergate_api/tests/apps/applications/__init__.py                     0      0   100%
   jobbergate_api/tests/apps/applications/test_application_files.py     104      0   100%
   jobbergate_api/tests/apps/applications/test_routers.py               368      0   100%
   jobbergate_api/tests/apps/applications/test_schemas.py                14      0   100%
   jobbergate_api/tests/apps/conftest.py                                 41      0   100%
   jobbergate_api/tests/apps/job_scripts/__init__.py                      0      0   100%
   jobbergate_api/tests/apps/job_scripts/conftest.py                     10      2    80%   32, 49
   jobbergate_api/tests/apps/job_scripts/test_job_script_files.py       102      0   100%
   jobbergate_api/tests/apps/job_scripts/test_routers.py                373      3    99%   48-64, 72
   jobbergate_api/tests/apps/job_submissions/__init__.py                  0      0   100%
   jobbergate_api/tests/apps/job_submissions/test_routers.py            483      0   100%
   jobbergate_api/tests/apps/test_main.py                                 7      0   100%
   jobbergate_api/tests/conftest.py                                     114      1    99%   127
   jobbergate_api/tests/test_config.py                                   33      0   100%
   jobbergate_api/tests/test_email_notification.py                       44      0   100%
   jobbergate_api/tests/test_file_validation.py                          17      0   100%
   jobbergate_api/tests/test_meta_mapper.py                              27      0   100%
   jobbergate_api/tests/test_pagination.py                               55      0   100%
   jobbergate_api/tests/test_s3_manager.py                               17      0   100%
   jobbergate_api/tests/test_security.py                                 39      0   100%
   jobbergate_api/tests/test_storage.py                                   7      0   100%
   ------------------------------------------------------------------------------------------------
   TOTAL                                                               3083     60    98%

   Required test coverage of 95.0% reached. Total coverage: 98.05%
   =========================================================== 158 passed, 130 warnings in 52.46s ===========================================================


Note that for the API, there must be a test database already running for it to connect
with.


Running Linters
---------------

The main subprojects each use a group of linting tools to make sure that the code
follows some standards. These linters will report any lines or segements of the code
that do not meet the project's standards.

To invoke all of the linters for a subproject, you may use ``make``:

.. code-block:: console

   make lint


If any issues are reported, fix the reported error and try running it again. The linters
will only succeed if all of the issues are fixed.


Running Formatters
------------------

For most of the linting issues, the code can be auto-corrected using the configured
code formatters.

Currently, the subprojects use the following formatters::

* `black`_
* `isort`_

To apply the formatters, you may use ``make``:

.. code-block:: console

   make format


The formatters will report any files that were changed in their reports.


Running Static Code Checkers
----------------------------

The Jobbergate subprojects include type-hints that must be checked using the `mypy`_
static code checker. It may invoked using ``make``:

.. code-block:: console

   make mypy

If any issues are located, they will be reported. Each type issue must be fixed before
the static type checker passes.


Running All Quality Checks
--------------------------

Finally, all of the quality checks can be run using ``make``:

.. code-block:: console

   make qa


.. _pytest: https://docs.pytest.org/en/7.1.x/
.. _black: https://black.readthedocs.io/en/stable/
.. _isort: https://github.com/PyCQA/isort
.. _mypy: http://www.mypy-lang.org/
.. _psycopg2: https://www.psycopg.org/docs/install.html

