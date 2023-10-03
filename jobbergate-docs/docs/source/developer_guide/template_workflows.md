# Job Script Template Workflow Files

**TODO**: Rewrite/update

The `jobbergate.py` is a python script that is used within an interactive framework
that gathers the values for template variables that will be needed when Job Scripts are
rendered from Applications.

Throughout the documentation, this file is referred to as the "Application Source."

The entire purpose of the Application Source is to construct a workflow of questions
organized in a series of that can be changed dynamically according to the answers
provided by the user.


## The JobbergateApplication class

Each Application Source script must define exactly one class named
`JobbergateApplication`.

This class should be a regular python class that inherits from the
`JobbergateApplicationBase`. This base class is imported from
[the application_base module](https://github.com/omnivector-solutions/jobbergate/blob/main/jobbergate-cli/jobbergate_cli/subapps/applications/applications_base.py).

The `JobbergateApplication` implementation may be a simple or complex as needed by
the user. However, it must define a `mainflow()` method which is the first of the
workflow methods that the Application processes.


## The workflow methods

The `mainflow()` method is essentially the entry point for the Application Source.
It must return a list of questions that should be asked to the user in order. These
questions will be used to gather the template variable values.

The `mainflow()` method must take a dictionary named `data` as a keyword argument.
This kwarg should default to `None`, and it should be set to an empty dict if the
default is not overridden.

Each workflow can also specify the net workflow method to call after its questions have
been asked and answered. In this way, the workflows can be organized in a dynamic series
where the path is dictated by the user responses.

The workflow methods specify the next flow in the sequence by setting an item keyed by
"nextworkflow" in the `data` dictionary. The value of this item is the name of the
next workflow method to call.

Each workflow method can examine the results from previous workflows by referencing the
`data` dict. All of the key/value pairs in the dictionary (besides "nextworkflow")
represent answers to previous questions.


## The Questions

The Application source is built around a question asking framework that defines
different sorts of questions that can be asked of the user.

The question types are defined by classes that derive from a base `QuestionBase`
class. The question types include::

* Text: gather a simple string response from the user
* Integer: gather a simple int response from the user
* List: prompt the user to select one item from a list
* Directory: prompt the user for a directory path
* File: prompt the user for a file path
* Checkbox: prompt the user to select as many items from a list as they want
* Confirm: prompt the user to offer a boolean response
* BooleanList: prompt a series of boolean resonses
* Const: set the variable to the default value without even asking the user

!!!note

  The BooleanList question has some very complex logic. The source code should be
  examined to understand what this does in detail.

All of the implementation of the quetion classes (including the base class) can be found
in [the questions module](https://github.com/omnivector-solutions/jobbergate/blob/main/jobbergate-cli/jobbergate_cli/subapps/applications/questions.py)
of the Jobbergate source code.


## Other class attributes

Each Application Source also has access to some attributes set up by the
`JobbergateApplicationBase`.

The `jobbergate_config` attribute will contain any of the properties that are set in
the `jobbergate_config` section of the Application Config (`jobbergate.yaml`).
These values can include anything set up by the user at application creation time.

The `application_config` attribute contains all of the properties that are set in the
`application_config` section of the Application config (`jobbergate.yaml`). This
section may be empty. If it is, the `application_config` atrribute will be an empty
dictionary. This dictionary should only be populated by the template variables that
the Application Source seeks to collect from the user. The values for each item are the
default values for that template variable.
