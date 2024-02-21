# JobTemplateListView

Schema for the response to get a list of entries.

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

## Example

```python
from openapi_client.models.job_template_list_view import JobTemplateListView

# TODO update the JSON string below
json = "{}"
# create an instance of JobTemplateListView from a JSON string
job_template_list_view_instance = JobTemplateListView.from_json(json)
# print the JSON string representation of the object
print JobTemplateListView.to_json()

# convert the object into a dict
job_template_list_view_dict = job_template_list_view_instance.to_dict()
# create an instance of JobTemplateListView from a dict
job_template_list_view_form_dict = job_template_list_view.from_dict(job_template_list_view_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


