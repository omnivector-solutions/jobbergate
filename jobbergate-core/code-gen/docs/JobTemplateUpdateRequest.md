# JobTemplateUpdateRequest

Schema for the request to update a job template.

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | The unique name of the instance | [optional] 
**identifier** | **str** | A human-friendly label used for lookup on frequently accessed applications | [optional] 
**description** | **str** | A text field providing a human-friendly description of the job_script | [optional] 
**template_vars** | **object** | The template variables of the job script template | [optional] 
**is_archived** | **bool** | Indicates if the job script template has been archived. | [optional] 

## Example

```python
from openapi_client.models.job_template_update_request import JobTemplateUpdateRequest

# TODO update the JSON string below
json = "{}"
# create an instance of JobTemplateUpdateRequest from a JSON string
job_template_update_request_instance = JobTemplateUpdateRequest.from_json(json)
# print the JSON string representation of the object
print JobTemplateUpdateRequest.to_json()

# convert the object into a dict
job_template_update_request_dict = job_template_update_request_instance.to_dict()
# create an instance of JobTemplateUpdateRequest from a dict
job_template_update_request_form_dict = job_template_update_request.from_dict(job_template_update_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


