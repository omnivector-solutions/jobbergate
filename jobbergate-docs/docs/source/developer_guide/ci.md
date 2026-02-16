# Continuous Integration

Jobbergate employs [GitHub actions](https://github.com/omnivector-solutions/jobbergate/actions) for its continuous
integration processes. Detailed descriptions of these actions are provided on this page.

## Automated Quality Assurance

Jobbergate's git repository incorporates a GitHub Action, specified in
[test_on_push.yaml](https://github.com/omnivector-solutions/jobbergate/blob/main/.github/workflows/test_on_push.yaml),
which is designed to execute our [quality assurance tools](./qa_tools.md) across all
Jobbergate sub-projects simultaneously. The action is activated anytime a new commit is
pushed to the `main` branch or whenever a pull request is submitted.

The suite of quality assurance tools encompasses unit tests, code coverage, linters,
code formatters, and static type checkers. Comprehensive documentation about each tool
is available in the [Quality Assurance Tools](./qa_tools.md) section.

## Automated Publication to PyPI

The major components of Jobbergate are published on PyPI, the Python Package Index.
They are available at:

- [jobbergate-api](https://pypi.org/project/jobbergate-api/)
- [jobbergate-cli](https://pypi.org/project/jobbergate-cli/)
- [jobbergate-agent](https://pypi.org/project/jobbergate-agent/)
- [jobbergate-core](https://pypi.org/project/jobbergate-core/)

These packages are automatically published to PyPI by three linked GitHub Actions that
are detailed below.

### Prepare for release

The first action involved in publication is the
[prepare_release.yaml](https://github.com/omnivector-solutions/jobbergate/blob/main/.github/workflows/prepare_release.yaml)
action. It is triggered manually on github through a "workflow dispatch event" whenever
new features or fixes need to be published.

The action takes two arguments that must be supplied by the user. They are:

- **Use workflow from:**
   The branch from which the release will be created. The default is `main`, and it's
   highly recommended that releases are cut from this branch in order to keep a linear
   commit history between releases and pre-releases.
- **Release Number:**
   This specifies the type of release that will be created, for instance, `1.2.3`, or `1.2.3a1`, `1.2.3b1`, `1.2.3rc1`, etc.
   Since Jobbergate uses semantic versioning, it's important to carefully select the
   correct type of release.

Once activated, this action:

- Creates a new dated entry on the changelog file using `towncrier`.
- Creates a new branch named `prepare-release/<version>`.
- Opens a draft pull request titled `Release <version>`.

In this way, all the changes above can be reviewed before the release is published,
and all quality assurance tests are executed for the pull request.

The remaining steps of the workflow are chained automatically once the PR is
accepted and merged into main.

### Create a new tag

The next action in the sequence is the
[tag_on_merged_pull_request.yaml](https://github.com/omnivector-solutions/jobbergate/blob/main/.github/workflows/tag_on_merged_pull_request.yaml)
action. Once the automatically created release PR is merged into the `main` branch, this
action is triggered. It creates and pushes a new git tag to GitHub. The tag is based on
the new version number for the release.

### Publish on Tag

The final action is
[publish_on_tag.yaml](https://github.com/omnivector-solutions/jobbergate/blob/main/.github/workflows/publish_on_tag.yaml)
This action is triggered when a new version tag is pushed to the repository.
It first double checks if the tag matches the version number of each Jobbergate
component, and then it builds and publishes the packages on PyPI.
