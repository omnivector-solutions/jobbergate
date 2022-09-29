===============
jobbergate.yaml
===============

The ``jobbergate.yaml`` is used to define configuration settings for a Jobbergate
Application and to define the template variables (and their defaults). The
YAML contains two sections; ``jobbergate_config`` and ``application_config``.

The Schema and examples are provided below.


Schema
------

.. code:: yaml

  application_config: dict (optional)

  jobbergate_config:
    default_template: string (required)
    supporting_files: list (optional)
    template_files: list (optional)


application_config
..................

This section defines the template variables that will be used to render the template(s)
into a Job Script. The template variables are the subjects of the interactive questions
that the applicaiton source code presents to users.

Jobbergate applications that inherit from ``JobbergateApplicationBase`` can access
``application_config`` via the ``application_config`` attribute of the class instance.

As an example, you may want to enforce that a computation only ever runs on a set of
well-defined partitions. To accomplish this using Jobbergate you can enforce that
Job Scripts are only be created for the well-defined partitions by defining the
partition name(s) as part of the ``application_config``. You can then access those
values in the ``JobbergateApplication`` instance when gathering template variable values
that are used to render job-scripts.

The ``application_config`` seciton would appear as:


.. code:: yaml

  # jobbergate.yaml
  application_config:
    partitions:
    - compute1
    - compute2


And the Application source code might look like:

.. code:: python

  # jobbergate.py

  from jobbergate_cli.application_base import JobbergateApplicationBase
  from jobbergate_cli import appform


  class JobbergateApplication(JobbergateApplicationBase):
      def mainflow(self, data):
          questions = []

          questions.append(appform.List(
              variablename="partition",
              message="Choose slurm partition:",
              choices=self.application_config['partitions'],
          ))
          return questions


jobbergate_config
.................

``jobbergate_config`` is used internally by Jobbergate and is a required configuration
of every jobbergate application. It can contain many different settings that may also
be used by the Application source code. However, it has a fixed schema that includes
``supporting_files``, ``default_template``, and ``template_files``.


template_files
``````````````

This is a list of the Job Script templates that are included in this Application. While
a single Application may include many templates, a Job Script is rendered only from one.
These files must all be `Jinja2 <https://jinja.palletsprojects.com/en/3.1.x/>`_
templates.


default_template
````````````````

This is just a reference to one of the enties in the ``template_files``. It describes
the template that will be rendered by default. However, if a different file is selected
during the Applications execution, this value (after execution) will be changed to the
Job Script template that will be rendered instad. It must match one of the entries in
``template_files`` exactly.


supporting_files
````````````````

This is a mapping of extra files that need to be included next to the Job Script when it
is submitted to the Slurm Cluster. Each entry contains the name of the file as it should
appear on the cluster as the key and the name of the file as it appears in the
application directory as the value.

Each of these files may also be a Jinja2 template that is rendrered by the values for
the template variables that are gathered during Application execution. These are not
Job Scripts themselves (usually!). This entry is not required.
