# JobScriptUpdateRequest

Request model for updating JobScript instances.

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | The unique name of the instance | [optional] 
**description** | **str** | A text field providing a human-friendly description of the job_script | [optional] 
**is_archived** | **bool** | Indicates if the job script has been archived. | [optional] 

## Example

```python
from openapi_client.models.job_script_update_request import JobScriptUpdateRequest

# TODO update the JSON string below
json = "{}"
# create an instance of JobScriptUpdateRequest from a JSON string
job_script_update_request_instance = JobScriptUpdateRequest.from_json(json)
# print the JSON string representation of the object
print JobScriptUpdateRequest.to_json()

# convert the object into a dict
job_script_update_request_dict = job_script_update_request_instance.to_dict()
# create an instance of JobScriptUpdateRequest from a dict
job_script_update_request_form_dict = job_script_update_request.from_dict(job_script_update_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


