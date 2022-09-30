=================
 S3 File Storage
=================

Besides the information kept in the database, application and job-scripts files are
stored in an S3 Bucket.

The bucket is named according to the ``S3_BUCKET_NAME`` environment variable used by
the Jobbergate API.

Within the the bucket, there should be two top-level folders, and the structure should
appear similar to:

.. code-block::

    <S3_BUCKET_NAME>
    ├── applications
    │   ├── 1
    │   │   ├── jobbergate.yaml
    │   │   ├── jobbergate.py
    │   │   ├── template1.py.j2
    │   │   └── template2.py.j2
    │   └── 2
    │       ├── jobbergate.yaml
    │       ├── jobbergate.py
    │       └── template.py.j2
    └── job-scripts
        ├── 11
        │    └── jobbergate.txt
        └── 12
             └── jobbergate.txt


applications
------------

This 'folder' will contain all the files uploaded for Applications. Each entry in this
folder will be named with a single integer that corresponds to the ``id`` for the
Application's entry in the database.

Within each one of the individual application folders, there will be the following:

* jobbergate.py (the application source code)
* jobbergate.yaml (the application config),
* At least one template file with any file name and a ``.j2`` or ``jinja2`` extension.


job-scripts
-----------

This 'folder' will contain all the files uploaded for Job Scripts. Each entry in this
folder will be named with a single integer that corresponds to the ``id`` for the
Job Script's entry in the database.

Within each one of the individual application folders, there will be one text file
named ``jobergate.txt``. This will contain the rendered Job Script that will be
submitted to Slurm when a Job Submission is created.
