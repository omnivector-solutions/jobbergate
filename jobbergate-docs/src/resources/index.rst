======================
 Jobbergate Resources
======================

Jobbergate has three main resources (represented as database tables) that it uses to
manage job templating and submission. These are stored as tables in a postgres database
and are accessed through separate endpoints in the API and with separate subcommands in
the CLI.


Applications
------------

The Application resource is the combination of a Job Script template with a framework
for interactively gathering the template variable values from the user.

Applications are used to produce Job Scripts that may be submitted. An Application
folder contains:

* jobbergate.py: Source code for describing how to gather template variable value
* jobbergate.yaml: Configuration and default variable values
* templates: One or more `Jinja 2`_ templates that will be rendered with the supplied config


Job Scripts
-----------

This is the main resource. It provides the source code for the actual job that will run
on the Slurm clusters. Job Scripts are rendered from Applications; A single application
to generate many Job Scripts that vary by the parameters passed at creation time.


Job Submissions
---------------

Job Submissions stimply track the status and metadata for a Job Script that has been
submitted by Jobbergate to a Slurm cluster. It carries identification information that
tie it to both the Job Script in the Jobbergate data store and to the Job objects that
Slurm uses.


.. _`Jinja 2`: https://palletsprojects.com/p/jinja/
