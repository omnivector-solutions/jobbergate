# JobSubmissionAgentSubmittedRequest

Request model for marking JobSubmission instances as SUBMITTED.

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **int** | The unique database identifier for the instance | 
**slurm_job_id** | **int** | The id for the slurm job executing this job_submission | [optional] 

## Example

```python
from openapi_client.models.job_submission_agent_submitted_request import JobSubmissionAgentSubmittedRequest

# TODO update the JSON string below
json = "{}"
# create an instance of JobSubmissionAgentSubmittedRequest from a JSON string
job_submission_agent_submitted_request_instance = JobSubmissionAgentSubmittedRequest.from_json(json)
# print the JSON string representation of the object
print JobSubmissionAgentSubmittedRequest.to_json()

# convert the object into a dict
job_submission_agent_submitted_request_dict = job_submission_agent_submitted_request_instance.to_dict()
# create an instance of JobSubmissionAgentSubmittedRequest from a dict
job_submission_agent_submitted_request_form_dict = job_submission_agent_submitted_request.from_dict(job_submission_agent_submitted_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


