# JobScriptCreateRequest

Request model for creating JobScript instances.

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | The unique name of the instance | 
**description** | **str** | A text field providing a human-friendly description of the job_script | [optional] 

## Example

```python
from openapi_client.models.job_script_create_request import JobScriptCreateRequest

# TODO update the JSON string below
json = "{}"
# create an instance of JobScriptCreateRequest from a JSON string
job_script_create_request_instance = JobScriptCreateRequest.from_json(json)
# print the JSON string representation of the object
print JobScriptCreateRequest.to_json()

# convert the object into a dict
job_script_create_request_dict = job_script_create_request_instance.to_dict()
# create an instance of JobScriptCreateRequest from a dict
job_script_create_request_form_dict = job_script_create_request.from_dict(job_script_create_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


