# JobTemplateDetailedView

Schema for the request to an entry.  Notice the files default to None, as they are not always requested, to differentiate between an empty list when they are requested, but no file is found.

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **int** | The unique database identifier for the instance | 
**name** | **str** | The unique name of the instance | 
**owner_email** | **str** | The email of the owner/creator of the instance | 
**created_at** | **datetime** | The timestamp for when the instance was created | 
**updated_at** | **datetime** | The timestamp for when the instance was last updated | 
**is_archived** | **bool** | Indicates if the job script template has been archived. | 
**description** | **str** | A text field providing a human-friendly description of the job_script | [optional] 
**identifier** | **str** | A human-friendly label used for lookup on frequently accessed applications | [optional] 
**cloned_from_id** | **int** | Indicates the id this entry has been cloned from, if any. | [optional] 
**template_vars** | **object** | The template variables of the job script template | [optional] 
**template_files** | [**List[TemplateFileDetailedView]**](TemplateFileDetailedView.md) | The template files attached to a job script template | [optional] 
**workflow_files** | [**List[WorkflowFileDetailedView]**](WorkflowFileDetailedView.md) |  | [optional] 

## Example

```python
from openapi_client.models.job_template_detailed_view import JobTemplateDetailedView

# TODO update the JSON string below
json = "{}"
# create an instance of JobTemplateDetailedView from a JSON string
job_template_detailed_view_instance = JobTemplateDetailedView.from_json(json)
# print the JSON string representation of the object
print JobTemplateDetailedView.to_json()

# convert the object into a dict
job_template_detailed_view_dict = job_template_detailed_view_instance.to_dict()
# create an instance of JobTemplateDetailedView from a dict
job_template_detailed_view_form_dict = job_template_detailed_view.from_dict(job_template_detailed_view_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


