# PendingJobSubmission

Specialized model for the cluster-agent to pull pending job_submissions.  Model also includes data from its job_script and application sources.

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **int** | The unique database identifier for the instance | 
**name** | **str** | The unique name of the job submission | 
**owner_email** | **str** | The email of the owner/creator of the instance | 
**execution_directory** | **str** | The directory on the cluster where the job should be executed | [optional] 
**execution_parameters** | **object** | The parameters to be passed to the job submission. See more details at: https://slurm.schedmd.com/rest_api.html | [optional] 
**job_script** | [**JobScriptDetailedView**](JobScriptDetailedView.md) |  | 

## Example

```python
from openapi_client.models.pending_job_submission import PendingJobSubmission

# TODO update the JSON string below
json = "{}"
# create an instance of PendingJobSubmission from a JSON string
pending_job_submission_instance = PendingJobSubmission.from_json(json)
# print the JSON string representation of the object
print PendingJobSubmission.to_json()

# convert the object into a dict
pending_job_submission_dict = pending_job_submission_instance.to_dict()
# create an instance of PendingJobSubmission from a dict
pending_job_submission_form_dict = pending_job_submission.from_dict(pending_job_submission_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


