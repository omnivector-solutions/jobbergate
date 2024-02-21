# JobTemplateCreateRequest

Schema for the request to create a job template.

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | The unique name of the instance | 
**identifier** | **str** | A human-friendly label used for lookup on frequently accessed applications | [optional] 
**description** | **str** | A text field providing a human-friendly description of the job_script | [optional] 
**template_vars** | **object** | The template variables of the job script template | [optional] 

## Example

```python
from openapi_client.models.job_template_create_request import JobTemplateCreateRequest

# TODO update the JSON string below
json = "{}"
# create an instance of JobTemplateCreateRequest from a JSON string
job_template_create_request_instance = JobTemplateCreateRequest.from_json(json)
# print the JSON string representation of the object
print JobTemplateCreateRequest.to_json()

# convert the object into a dict
job_template_create_request_dict = job_template_create_request_instance.to_dict()
# create an instance of JobTemplateCreateRequest from a dict
job_template_create_request_form_dict = job_template_create_request.from_dict(job_template_create_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


