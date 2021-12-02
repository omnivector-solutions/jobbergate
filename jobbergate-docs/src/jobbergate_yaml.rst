===============
jobbergate.yaml
===============

The ``jobbergate.yaml`` is used to define jobbergate application level and jobbergate internal
configuration. The ``jobbergate.yaml`` contains two sections; ``jobbergate_config`` and ``application_config``.

Find below the schema, examples and further documentation for ``jobbergate.yaml``.

------
Schema
------

.. code:: yaml

  application_config: dict (optional)

  jobbergate_config:
    default_template: string (required)
    supporting_files: list (optional)
    supporting_files_output_name: dict (optional)
    template_files: list (optional)


*******************
application_config
*******************

Application configuration should contain values intended to be used as a part
of assembling questions inside of ``jobbergate.py``. Jobbergate applicatiions that
inherit from ``JobbergateApplicationBase`` can access ``application_config`` via the
``self.application_config`` attribute.

As an example, you may want to enforce that a computation only ever runs on
a set of well-defined partitions. To accomplish this using Jobbergate we can
enforce that job-scripts are only be created for the well-defined partitions
by defining the partition name(s) as part of the ``application_config``. We can then
access these values in the ``JobbergateApplication`` when assembling questions
and creating job-scripts.


The ``jobbergate.yaml`` and ``jobbergate.py`` would resemble the following:


.. code:: yaml

  # jobbergate.yaml

  ---
  application_config:
    partitions:
    - compute1
    - compute2


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


*******************
jobbergate_config
*******************

``jobbergate_config`` is used internally by Jobbergate and is a required configuration
of every jobbergate application.
