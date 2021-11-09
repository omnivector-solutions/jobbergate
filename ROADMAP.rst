=================================
 Roadmap for Next-gen Jobbergate
=================================

This explains the roadmap for migrating from the legacy jobbergate apps to the
next generation of Jobbergate.


Work Items::

    [x] Add capability to dump full json output from legacy jobbergate-cli
    [x] Rename jobbergate-api-fastapi to jobbergate
    [x] Move jobbergate-api-fastapi code to sub-project in jobbergate/jobbergate-api
    [ ] Migrate jobbergate-cli v2 branch to sub-project in jobbergate/jobbergate-cli
    [ ] Migrate new additions from legacy jobbergate-cli to jobbergate/jobbergate-cli
    [ ] Add Dockerfile to jobbergate/jobbergate-cli
    [ ] Move jobbergate-documentation projet to subproject in jobbergate/jobbergate-doc
    [ ] Add support for Auth0 authorized requests to jobbergate/jobbergate-cli
    [ ] Add docker-compose to jobbergate
    [ ] Add minio to docker-compose for jobbergate/jobbergate-cli in lieu of AWS S3
    [ ] Add capability to dump user map from legacy jobbergate-cli
    [ ] Add scripts for importing data from jobbergate-cli json dumps to jobbergate
