# PageJobSubmissionListView


## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**items** | [**List[JobSubmissionListView]**](JobSubmissionListView.md) |  | 
**total** | **int** |  | 
**page** | **int** |  | [optional] 
**size** | **int** |  | [optional] 
**pages** | **int** |  | [optional] 

## Example

```python
from openapi_client.models.page_job_submission_list_view import PageJobSubmissionListView

# TODO update the JSON string below
json = "{}"
# create an instance of PageJobSubmissionListView from a JSON string
page_job_submission_list_view_instance = PageJobSubmissionListView.from_json(json)
# print the JSON string representation of the object
print PageJobSubmissionListView.to_json()

# convert the object into a dict
page_job_submission_list_view_dict = page_job_submission_list_view_instance.to_dict()
# create an instance of PageJobSubmissionListView from a dict
page_job_submission_list_view_form_dict = page_job_submission_list_view.from_dict(page_job_submission_list_view_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


