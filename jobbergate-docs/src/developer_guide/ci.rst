========================
 Continuous Integration
========================

Jobbergate uses `GitHub actions <https://github.com/omnivector-solutions/jobbergate/actions>`_ as continuous integration tools. They are described in detail on this page.

Quality Assurance
-----------------

A dedicated GitHub action is included at Jobbergate's repository 
(`test_on_push.yaml <https://github.com/omnivector-solutions/jobbergate/blob/main/.github/workflows/test_on_push.yaml>`_)
to run the quality assurance tools for all sub-projects at once.
They include unit tests, code coverage, linters, code formatters, and static type checkers.
Each is detailed in the section :any:`Quality Assurance Tools`.
This action is triggered whenever a new commit is pushed to the ``main`` branch or to a pull request.

Publish on PyPI
---------------

The major components of Jobbergate are published on PyPI, the Python Package Index.
They are available at:

* `jobbergate-api <https://pypi.org/project/jobbergate-api/>`_
* `jobbergate-cli <https://pypi.org/project/jobbergate-cli/>`_

The steps to publish them to PyPI are automatized by three GitHub actions,
that are better described bellow.

Prepare for release
^^^^^^^^^^^^^^^^^^^

This action
(`prepare_release.yaml <https://github.com/omnivector-solutions/jobbergate/blob/main/.github/workflows/prepare_release.yaml>`_)
is triggered on a workflow dispatch event and demands some interactions
to ensure code quality. It takes as arguments:

* The base branch from which the action will run. Notice that the use of the ``main``
  branch is highly recommended in order to keep a linear commit history between releases and pre-releases.
* The bump version rule to be applied, based on
  `Poetry version <https://python-poetry.org/docs/cli/#version>`_.
  The following options are presented in a drop-down menu:
  ``patch``, ``minor``, ``major``, ``prepatch``, ``preminor``, ``premajor``, ``prerelease``.

Once activated, this action:

* Uses Poetry to bump the version number of all the Jobbergate packages.
* Checks if the new version number is synchronized between them, and fails if they are not.
* Creates a new entry on each changelog file with the new version number and the current date,
  including all unreleased features and bug fixes.
* Creates a new branch named ``release/<version>``.
* Opens a draft pull request titled ``Release <version>``.
  In this way, all the changes above can be reviewed before the release is published,
  and all quality assurance tests are executed for the pull request.

The remaining steps of the workflow are chained automatically once the PR is
accepted and merged into main.

Create a new tag
^^^^^^^^^^^^^^^^

When a release PR is merged into the ``main`` branch, this action
(`tag_on_merged_pull_request.yaml <https://github.com/omnivector-solutions/jobbergate/blob/main/.github/workflows/tag_on_merged_pull_request.yaml>`_)
is triggered. It creates and pushes a new tag to the repository, based on the new version number.

Publish on Tag
^^^^^^^^^^^^^^

This action
(`publish_on_tag.yaml <https://github.com/omnivector-solutions/jobbergate/blob/main/.github/workflows/publish_on_tag.yaml>`_)
is finally triggered when a new version tag is pushed to the repository.
It first double checks if the tag matches the version number of each Jobbergate component, and then
it builds and publishes the packages on PyPI.