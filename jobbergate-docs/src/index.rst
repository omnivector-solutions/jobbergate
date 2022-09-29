================================
 Jobbergate Documentation Pages
================================

This documentation explains the purpose, installation, and usage of the
Jobbergate system.

Jobbergate is a job templating and submission system that integrates with Slurm to
enable the re-use and remote submission of job scripts to a Slurm cluster.

The best way to understand Jobbergate is to look at it in terms of the three Resources
that it uses and the three Apps that interact with them.

There is also a Devloper Guide provided for details about interacting with Jobbergate,
testing the platform, and adding more functionaly to it.


Table of Contents
-----------------

.. toctree::
   :maxdepth: 2

   Apps <apps>
   Resources <resources>
   Tutorial <tutorial>
   Developer Guide <developer_guide/index>
   Attribution <attribution>


TODO
----

* Write tutorial using docker-compose
* Write a CI doc
* Write "Setting up keycloak" guide
