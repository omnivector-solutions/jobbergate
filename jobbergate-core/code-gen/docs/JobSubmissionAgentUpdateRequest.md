# JobSubmissionAgentUpdateRequest

Request model for updating JobSubmission instances.

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**slurm_job_id** | **int** | The id for the slurm job executing this job_submission | 
**slurm_job_state** | [**SlurmJobState**](SlurmJobState.md) | The Slurm Job state as reported by the agent.example | 
**slurm_job_info** | **str** | Detailed information about the Slurm Job as reported by the agent | 
**slurm_job_state_reason** | **str** |  | [optional] 

## Example

```python
from openapi_client.models.job_submission_agent_update_request import JobSubmissionAgentUpdateRequest

# TODO update the JSON string below
json = "{}"
# create an instance of JobSubmissionAgentUpdateRequest from a JSON string
job_submission_agent_update_request_instance = JobSubmissionAgentUpdateRequest.from_json(json)
# print the JSON string representation of the object
print JobSubmissionAgentUpdateRequest.to_json()

# convert the object into a dict
job_submission_agent_update_request_dict = job_submission_agent_update_request_instance.to_dict()
# create an instance of JobSubmissionAgentUpdateRequest from a dict
job_submission_agent_update_request_form_dict = job_submission_agent_update_request.from_dict(job_submission_agent_update_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


