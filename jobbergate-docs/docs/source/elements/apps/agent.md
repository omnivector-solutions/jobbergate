# Jobbergate Agent Overview

The [Jobbergate Agent](https://github.com/omnivector-solutions/jobbergate/jobbergate-agent)
is a daemon application that is designed to be integrated into the slurm cluster.

It predominantly fulfills two key roles:

* Submitting newly created Job Submissions to the Slurm cluster
* Monitoring and updating the status of Job Submissions as they undergo processing

## Submitting Jobs


The Jobbergate Agent constantly monitors the Job Submissions resource for entries marked with
a `CREATED` status. These are Job Submissions that the API has instantiated but are yet to be
dispatched to Slurm.

When submitting a job to Slurm, the Jobbergate Agent pulls the Job Script itself plus any
supporting files associated with it down to the cluster. Once all the files have been downloaded,
the Job Script is submitted to Slurm via it's RESTful API. The Job Submission saves the identifier
for the Slurm Job so that it can be associated with the Job Script that was submitted. The Job
Submission also tracks all of the supporting files and submission parameters that were submitted
along with the Job Script.

Upon job submission to Slurm, the Jobbergate Agent retrieves not only the Job Script but also any
related supporting files, downloading them to the cluster. After ensuring all files are downloaded,
the Job Script is dispatched to Slurm through its RESTful API. The Job Submission retains the
unique identifier for the Slurm Job, ensuring it's linked to the submitted Job Script.
Additionally, the Job Submission logs all the supporting files and submission parameters that were
provided in tandem with the Job Script at submission time.


## Updating Job Status

Once submitted, the Jobbergate Agent updates the status of the Job Submission to `SUBMITTED`.
If there is an error during the submission process, the Agent sets the Job Submission
status to `REJECTED`.

Upon completion of the job by the Slurm cluster, the Agent updates the status either to
`DONE` if successful, or `ABORTED` if the job terminated without completion for any reason.
This signifies the conclusion of tasks related to that particular Job Submission.


# Usage

The Jobbergate Agent operates in the background; it's designed to be initiated and left uninterrupted.

For insights into its ongoing operations, the Agent offers detailed logging which can be analyzed.
