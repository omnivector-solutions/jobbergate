# JobSubmissionCreateRequest

Request model for creating JobSubmission instances.

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | The unique name of the job submission | 
**description** | **str** | A text field providing a human-friendly description of the job_submission | [optional] 
**job_script_id** | **int** | The foreign-key to the job_script from which this instance was created | 
**slurm_job_id** | **int** | The id for the slurm job executing this job_submission | [optional] 
**execution_directory** | **str** | The directory on the cluster where the job should be executed | [optional] 
**client_id** | **str** | The client_id of the cluster where this job submission should execute | [optional] 
**execution_parameters** | [**JobProperties**](JobProperties.md) | The parameters to be passed to the job submission. See more details at: https://slurm.schedmd.com/rest_api.html | [optional] 

## Example

```python
from openapi_client.models.job_submission_create_request import JobSubmissionCreateRequest

# TODO update the JSON string below
json = "{}"
# create an instance of JobSubmissionCreateRequest from a JSON string
job_submission_create_request_instance = JobSubmissionCreateRequest.from_json(json)
# print the JSON string representation of the object
print JobSubmissionCreateRequest.to_json()

# convert the object into a dict
job_submission_create_request_dict = job_submission_create_request_instance.to_dict()
# create an instance of JobSubmissionCreateRequest from a dict
job_submission_create_request_form_dict = job_submission_create_request.from_dict(job_submission_create_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


