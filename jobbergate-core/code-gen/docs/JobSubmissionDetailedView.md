# JobSubmissionDetailedView

Complete model to match the database for the JobSubmission resource.

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **int** | The unique database identifier for the instance | 
**name** | **str** | The unique name of the job submission | 
**owner_email** | **str** | The email of the owner/creator of the instance | 
**created_at** | **datetime** | The timestamp for when the instance was created | 
**updated_at** | **datetime** | The timestamp for when the instance was last updated | 
**is_archived** | **bool** | Indicates if the job submission has been archived. | 
**description** | **str** | A text field providing a human-friendly description of the job_submission | [optional] 
**job_script_id** | **int** | The foreign-key to the job_script from which this instance was created | [optional] 
**slurm_job_id** | **int** | The id for the slurm job executing this job_submission | [optional] 
**client_id** | **str** | The client_id of the cluster where this job submission should execute | 
**status** | [**JobSubmissionStatus**](JobSubmissionStatus.md) | The status of the job submission. Must be one of CREATED, SUBMITTED, REJECTED, DONE, ABORTED | 
**slurm_job_state** | [**SlurmJobState**](SlurmJobState.md) | The Slurm Job state as reported by the agent.example | [optional] 
**job_script** | [**JobScriptListView**](JobScriptListView.md) |  | [optional] 
**execution_directory** | **str** | The directory on the cluster where the job should be executed | [optional] 
**report_message** | **str** | The report message received from cluster-agent when a job submission is rejected | [optional] 
**execution_parameters** | [**JobProperties**](JobProperties.md) | The parameters to be passed to the job submission. See more details at: https://slurm.schedmd.com/rest_api.html | [optional] 
**slurm_job_info** | **str** | Detailed information about the Slurm Job as reported by the agent | [optional] 

## Example

```python
from openapi_client.models.job_submission_detailed_view import JobSubmissionDetailedView

# TODO update the JSON string below
json = "{}"
# create an instance of JobSubmissionDetailedView from a JSON string
job_submission_detailed_view_instance = JobSubmissionDetailedView.from_json(json)
# print the JSON string representation of the object
print JobSubmissionDetailedView.to_json()

# convert the object into a dict
job_submission_detailed_view_dict = job_submission_detailed_view_instance.to_dict()
# create an instance of JobSubmissionDetailedView from a dict
job_submission_detailed_view_form_dict = job_submission_detailed_view.from_dict(job_submission_detailed_view_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


