# JobSubmissionAgentRejectedRequest

Request model for marking JobSubmission instances as REJECTED.

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **int** | The unique database identifier for the instance | 
**report_message** | **str** | The report message received from cluster-agent when a job submission is rejected | 

## Example

```python
from openapi_client.models.job_submission_agent_rejected_request import JobSubmissionAgentRejectedRequest

# TODO update the JSON string below
json = "{}"
# create an instance of JobSubmissionAgentRejectedRequest from a JSON string
job_submission_agent_rejected_request_instance = JobSubmissionAgentRejectedRequest.from_json(json)
# print the JSON string representation of the object
print JobSubmissionAgentRejectedRequest.to_json()

# convert the object into a dict
job_submission_agent_rejected_request_dict = job_submission_agent_rejected_request_instance.to_dict()
# create an instance of JobSubmissionAgentRejectedRequest from a dict
job_submission_agent_rejected_request_form_dict = job_submission_agent_rejected_request.from_dict(job_submission_agent_rejected_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


