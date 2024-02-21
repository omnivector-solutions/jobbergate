# PageActiveJobSubmission


## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**items** | [**List[ActiveJobSubmission]**](ActiveJobSubmission.md) |  | 
**total** | **int** |  | 
**page** | **int** |  | [optional] 
**size** | **int** |  | [optional] 
**pages** | **int** |  | [optional] 

## Example

```python
from openapi_client.models.page_active_job_submission import PageActiveJobSubmission

# TODO update the JSON string below
json = "{}"
# create an instance of PageActiveJobSubmission from a JSON string
page_active_job_submission_instance = PageActiveJobSubmission.from_json(json)
# print the JSON string representation of the object
print PageActiveJobSubmission.to_json()

# convert the object into a dict
page_active_job_submission_dict = page_active_job_submission_instance.to_dict()
# create an instance of PageActiveJobSubmission from a dict
page_active_job_submission_form_dict = page_active_job_submission.from_dict(page_active_job_submission_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


