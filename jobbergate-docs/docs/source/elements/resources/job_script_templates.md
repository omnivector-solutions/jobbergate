# Job Script Templates

The Job Scripts Templates are composed of the combination of a Job Script template with a framework
for interactively gathering the template variable values from the user.

Job Script Templates are used to produce Job Scripts that may be submitted.

A Job Script Template is composed of:

**TODO**: Rewrite all of this after this line

An Application
folder contains:

* jobbergate.py: Source code for describing how to gather template variable value
* jobbergate.yaml: Configuration and default variable values
* templates: One or more [Jinja 2](https://palletsprojects.com/p/jinja/) templates that will be rendered with the
  supplied config
