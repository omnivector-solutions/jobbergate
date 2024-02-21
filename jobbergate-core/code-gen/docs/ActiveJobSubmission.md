# ActiveJobSubmission

Specialized model for the cluster-agent to pull an active job_submission.

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **int** |  | 
**name** | **str** |  | 
**slurm_job_id** | **int** |  | 

## Example

```python
from openapi_client.models.active_job_submission import ActiveJobSubmission

# TODO update the JSON string below
json = "{}"
# create an instance of ActiveJobSubmission from a JSON string
active_job_submission_instance = ActiveJobSubmission.from_json(json)
# print the JSON string representation of the object
print ActiveJobSubmission.to_json()

# convert the object into a dict
active_job_submission_dict = active_job_submission_instance.to_dict()
# create an instance of ActiveJobSubmission from a dict
active_job_submission_form_dict = active_job_submission.from_dict(active_job_submission_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


