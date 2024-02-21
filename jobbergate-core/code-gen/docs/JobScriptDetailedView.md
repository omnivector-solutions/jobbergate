# JobScriptDetailedView

Model to match database for the JobScript resource.

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **int** | The unique database identifier for the instance | 
**name** | **str** | The unique name of the instance | 
**owner_email** | **str** | The email of the owner/creator of the instance | 
**created_at** | **datetime** | The timestamp for when the instance was created | 
**updated_at** | **datetime** | The timestamp for when the instance was last updated | 
**is_archived** | **bool** | Indicates if the job script has been archived. | 
**description** | **str** | A text field providing a human-friendly description of the job_script | [optional] 
**parent_template_id** | **int** | The foreign-key to the job script template from which this instance was created | [optional] 
**template** | [**JobTemplateListView**](JobTemplateListView.md) |  | [optional] 
**cloned_from_id** | **int** | Indicates the id this entry has been cloned from, if any. | [optional] 
**files** | [**List[JobScriptFileDetailedView]**](JobScriptFileDetailedView.md) |  | [optional] 

## Example

```python
from openapi_client.models.job_script_detailed_view import JobScriptDetailedView

# TODO update the JSON string below
json = "{}"
# create an instance of JobScriptDetailedView from a JSON string
job_script_detailed_view_instance = JobScriptDetailedView.from_json(json)
# print the JSON string representation of the object
print JobScriptDetailedView.to_json()

# convert the object into a dict
job_script_detailed_view_dict = job_script_detailed_view_instance.to_dict()
# create an instance of JobScriptDetailedView from a dict
job_script_detailed_view_form_dict = job_script_detailed_view.from_dict(job_script_detailed_view_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


