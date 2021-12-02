.. figure:: /src/_images/logo.png?raw=true
   :alt: Logo
   :align: center
   :width: 80px

   An Omnivector Solutions initiative

==========================
 Jobbergate Documentation
==========================

This repository contains the source for the Jobbergate documentation.

It uses [sphinx](https://www.sphinx-doc.org/en/master/) to render html pages from
the sourc ReStructuredText documents.


Build
=====

To build the documentation website, run the following command::

    $ make docs


Other Commands
==============

To lint the python files in the ``src`` directory, run::

    $ make lint


To clean up build artifacts, run::

    $ make clean
