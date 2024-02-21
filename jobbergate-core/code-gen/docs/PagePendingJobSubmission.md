# PagePendingJobSubmission


## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**items** | [**List[PendingJobSubmission]**](PendingJobSubmission.md) |  | 
**total** | **int** |  | 
**page** | **int** |  | [optional] 
**size** | **int** |  | [optional] 
**pages** | **int** |  | [optional] 

## Example

```python
from openapi_client.models.page_pending_job_submission import PagePendingJobSubmission

# TODO update the JSON string below
json = "{}"
# create an instance of PagePendingJobSubmission from a JSON string
page_pending_job_submission_instance = PagePendingJobSubmission.from_json(json)
# print the JSON string representation of the object
print PagePendingJobSubmission.to_json()

# convert the object into a dict
page_pending_job_submission_dict = page_pending_job_submission_instance.to_dict()
# create an instance of PagePendingJobSubmission from a dict
page_pending_job_submission_form_dict = page_pending_job_submission.from_dict(page_pending_job_submission_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


