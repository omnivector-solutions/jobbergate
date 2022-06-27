=======================
Implementations Details
=======================

Jobbergate-API
==============

Storage
-------

Besides the information kept in the database, application and job-scripts files are stored on a S3 Bucket as tarfiles and text files, respectively.
The bucket is named ``jobbergate-staging-eu-north-1-resources`` by default, but it can be changed using the configuration ``S3_BUCKET_NAME``.
The files are arranged in a directory for each, followed in the next level by the ``id`` number, and finally the filename (``jobbergate.tar.gz`` for applications and ``jobbergate.txt`` for job-scripts). See the example:

::

    <S3_BUCKET_NAME>
    ├── applications
    │   ├── 1
    │   │   └── jobbergate.tar.gz
    │   └── 2
    │       └── jobbergate.tar.gz
    └── job-scripts
        ├── 1
        │   └── jobbergate.txt
        └── 2
            └── jobbergate.txt