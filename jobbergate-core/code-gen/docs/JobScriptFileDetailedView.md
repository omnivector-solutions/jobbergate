# JobScriptFileDetailedView

Model for the job_script_files field of the JobScript resource.

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**parent_id** | **int** | The unique database identifier for the parent of this instance | 
**filename** | **str** | The name of the file | 
**file_type** | [**FileType**](FileType.md) | The type of the file | 
**created_at** | **datetime** | The timestamp for when the instance was created | [optional] 
**updated_at** | **datetime** | The timestamp for when the instance was last updated | [optional] 

## Example

```python
from openapi_client.models.job_script_file_detailed_view import JobScriptFileDetailedView

# TODO update the JSON string below
json = "{}"
# create an instance of JobScriptFileDetailedView from a JSON string
job_script_file_detailed_view_instance = JobScriptFileDetailedView.from_json(json)
# print the JSON string representation of the object
print JobScriptFileDetailedView.to_json()

# convert the object into a dict
job_script_file_detailed_view_dict = job_script_file_detailed_view_instance.to_dict()
# create an instance of JobScriptFileDetailedView from a dict
job_script_file_detailed_view_form_dict = job_script_file_detailed_view.from_dict(job_script_file_detailed_view_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


