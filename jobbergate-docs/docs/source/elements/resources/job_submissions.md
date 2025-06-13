# Job Submissions

Job Submissions primarily monitor the status and metadata of a [Job Script](./job_scripts.md) dispatched by Jobbergate
to a Slurm cluster. They possess identifying details linking them to the Job Script that was submitted and to the
corresponding Job objects created by Slurm.

## Data Model

```mermaid
erDiagram
    JobSubmission {
        int id pk
        int job_script_id fk
        str execution_directory
        int slurm_job_id
        enum[str] slurm_job_state
        str slurm_job_info
        str client_id
        enum[str] status
        str report_message
        list[str] sbatch_arguments
        str name
        str description
        str owner_email
        datetime created_at
        datetime updated_at
        bool is_archived
    }
```
