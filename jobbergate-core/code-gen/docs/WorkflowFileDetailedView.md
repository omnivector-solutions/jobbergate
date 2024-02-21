# WorkflowFileDetailedView

Schema for the response to get a workflow file.

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**parent_id** | **int** | The unique database identifier for the parent of this instance | 
**filename** | **str** | The name of the file | 
**runtime_config** | **object** | The runtime configuration of the workflow | [optional] 
**created_at** | **datetime** | The timestamp for when the instance was created | [optional] 
**updated_at** | **datetime** | The timestamp for when the instance was last updated | [optional] 

## Example

```python
from openapi_client.models.workflow_file_detailed_view import WorkflowFileDetailedView

# TODO update the JSON string below
json = "{}"
# create an instance of WorkflowFileDetailedView from a JSON string
workflow_file_detailed_view_instance = WorkflowFileDetailedView.from_json(json)
# print the JSON string representation of the object
print WorkflowFileDetailedView.to_json()

# convert the object into a dict
workflow_file_detailed_view_dict = workflow_file_detailed_view_instance.to_dict()
# create an instance of WorkflowFileDetailedView from a dict
workflow_file_detailed_view_form_dict = workflow_file_detailed_view.from_dict(workflow_file_detailed_view_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


