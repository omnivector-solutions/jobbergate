# JobScriptCloneRequest

Request model for cloning JobScript instances.

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | The unique name of the instance | [optional] 
**description** | **str** | A text field providing a human-friendly description of the job_script | [optional] 

## Example

```python
from openapi_client.models.job_script_clone_request import JobScriptCloneRequest

# TODO update the JSON string below
json = "{}"
# create an instance of JobScriptCloneRequest from a JSON string
job_script_clone_request_instance = JobScriptCloneRequest.from_json(json)
# print the JSON string representation of the object
print JobScriptCloneRequest.to_json()

# convert the object into a dict
job_script_clone_request_dict = job_script_clone_request_instance.to_dict()
# create an instance of JobScriptCloneRequest from a dict
job_script_clone_request_form_dict = job_script_clone_request.from_dict(job_script_clone_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


