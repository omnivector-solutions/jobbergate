# JobSubmissionUpdateRequest

Request model for updating JobSubmission instances.

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | The unique name of the job submission | [optional] 
**description** | **str** | A text field providing a human-friendly description of the job_submission | [optional] 
**execution_directory** | **str** | The directory on the cluster where the job should be executed | [optional] 
**status** | [**JobSubmissionStatus**](JobSubmissionStatus.md) | The status of the job submission. Must be one of CREATED, SUBMITTED, REJECTED, DONE, ABORTED | [optional] 

## Example

```python
from openapi_client.models.job_submission_update_request import JobSubmissionUpdateRequest

# TODO update the JSON string below
json = "{}"
# create an instance of JobSubmissionUpdateRequest from a JSON string
job_submission_update_request_instance = JobSubmissionUpdateRequest.from_json(json)
# print the JSON string representation of the object
print JobSubmissionUpdateRequest.to_json()

# convert the object into a dict
job_submission_update_request_dict = job_submission_update_request_instance.to_dict()
# create an instance of JobSubmissionUpdateRequest from a dict
job_submission_update_request_form_dict = job_submission_update_request.from_dict(job_submission_update_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


