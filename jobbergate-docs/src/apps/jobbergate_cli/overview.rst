================
 Jobbergate CLI
================

The primary purpose of the `Jobbergate CLI`_ is to provide interactive access to the Jobbergate API's features via a
command-line interface.

There are two primary modes used:

* Creating resources
* Viewing resources

For creating resources, the CLI provides ``create`` subcommands for each resource that allow the user to create new
instances. The Application resource is created by uploading files along with some metadata about the application. The
Job Script resources are created in the CLI by rendering templates in the Application resource into new Job Script
instances. The Job Submission resources are created by submitting a Job Script to a connected Slurm Cluster.

For viewing resoruces, the CLI provides ``list`` and ``get-one`` subcommands for each resource. These commands allow
the user to view varying levels of details about the instances that exist in the database.

The Jobbergate CLI can also be used to sign in to the Jobbergate API and to retrieve the auth token that is used to
identify the current user. This token can then be used for accessing the Jobbergate API through other means.


.. _`Jobbergate CLI`: https://github.com/omnivector-solutions/jobbergate/jobbergate-cli
