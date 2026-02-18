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


# Configuration

## User Mapping

The Jobbergate Agent supports different strategies for mapping Jobbergate user email addresses to local Slurm usernames. This is controlled by the `JOBBERGATE_AGENT_SLURM_USER_MAPPER` setting.

### Single User Mapper (Default)

The single user mapper maps all Jobbergate users to a single Slurm user. This is useful for development environments or clusters where all jobs should run under a single service account.

```bash
JOBBERGATE_AGENT_SLURM_USER_MAPPER="single-user-mapper"
```

If `SLURM_USER_MAPPER` is not specified, this is the default behavior.

### LDAP User Mapper

The LDAP user mapper queries an LDAP/Active Directory server to map user email addresses to their corresponding Slurm usernames. This enables multi-user support where each user runs jobs under their own Slurm account.

To enable LDAP user mapping, configure the following environment variables:

```bash
JOBBERGATE_AGENT_SLURM_USER_MAPPER="ldap-cached-mapper"
JOBBERGATE_AGENT_LDAP_URI="ldap://ldap.example.com:389"
JOBBERGATE_AGENT_LDAP_DOMAIN="example.com"
JOBBERGATE_AGENT_LDAP_USERNAME="service-account"
JOBBERGATE_AGENT_LDAP_PASSWORD="password"
```

**Configuration Parameters:**

- `SLURM_USER_MAPPER`: Set to `ldap-cached-mapper` to enable LDAP user mapping
- `LDAP_URI`: The URI of the LDAP server
  - For standard LDAP: `ldap://ldap.example.com:389`
  - For LDAPS (SSL): `ldaps://ldap.example.com:636`
- `LDAP_DOMAIN`: The fully qualified domain name used for:
  - NTLM authentication (e.g., `example.com`)
  - Constructing the search base (e.g., `example.com` becomes `DC=example,DC=com`)
- `LDAP_USERNAME`: Service account username with read access to user directory
- `LDAP_PASSWORD`: Service account password

**Caching:**

The LDAP mapper caches user lookups in a local SQLite database to improve performance and reduce LDAP server load. The cache database is stored in the agent's cache directory (by default `~/.cache/jobbergate-agent/user_mapper.sqlite3`).

**LDAP Search:**

When looking up a user, the agent:
1. Searches the LDAP directory for the user's email address
2. Retrieves the user's `cn` (common name) attribute as their Slurm username
3. Caches the mapping for future requests

# Usage

The Jobbergate Agent operates in the background; it's designed to be initiated and left uninterrupted.

For insights into its ongoing operations, the Agent offers detailed logging which can be analyzed.

A complete configuration example is available in the `.env.example` file in the jobbergate-agent directory.
