===========================
 Jobbergate Agent Overview
===========================

The `Jobbergate Agent <https://github.com/omnivector-solutions/jobbergate/jobbergate-agent>`_
is a daemon app that is installed on the Slurm cluster.

It performs two primary functions:

* Submitting newly created Job Submissions to the Slurm cluster
* Updating the status on Job Submissions as they are processed

Submitting Jobs
---------------

To find which Job Submissions need to be passed on to the Slurm cluster, The Jobbergate Agent
watches the Job Submissions resource for entries with a ``CREATED`` status. Job Submissions in
this status have been created by the API but have not yet been submitted to Slurm.

When submitting a job to Slurm, the Jobbergate Agent must first pull all the files for the job
from the Job Script entry from which the Job Submission was created. Once all the files have
been dowloaded, the job is submitted by a POST call to the Slurm Rest API with the Job Script
files and paramters.

Updating Job Status
-------------------

Once submitted, the Jobbergate Agent updates the status of the Job Submission to ``SUBMITTED``.
If there is an error during the submission process, the Agent will set the Job Submission
status to ``REJECTED``.

Finally, when the Slurm cluster is finished running the job, the Agent will update the status
to ``COMPLETE`` or ``FAILED`` to indicate that work for that Job Submission is finished.
cluster, and then submits them through Slurm. It also updates the status for jobs that are
complete or have failed.
