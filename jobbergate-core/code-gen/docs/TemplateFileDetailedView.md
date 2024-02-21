# TemplateFileDetailedView

Schema for the response to get a template file.

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**parent_id** | **int** | The unique database identifier for the parent of this instance | 
**filename** | **str** | The name of the file | 
**file_type** | [**FileType**](FileType.md) | The type of the file | 
**created_at** | **datetime** | The timestamp for when the instance was created | 
**updated_at** | **datetime** | The timestamp for when the instance was last updated | 

## Example

```python
from openapi_client.models.template_file_detailed_view import TemplateFileDetailedView

# TODO update the JSON string below
json = "{}"
# create an instance of TemplateFileDetailedView from a JSON string
template_file_detailed_view_instance = TemplateFileDetailedView.from_json(json)
# print the JSON string representation of the object
print TemplateFileDetailedView.to_json()

# convert the object into a dict
template_file_detailed_view_dict = template_file_detailed_view_instance.to_dict()
# create an instance of TemplateFileDetailedView from a dict
template_file_detailed_view_form_dict = template_file_detailed_view.from_dict(template_file_detailed_view_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


