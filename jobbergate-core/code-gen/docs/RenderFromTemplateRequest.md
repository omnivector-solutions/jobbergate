# RenderFromTemplateRequest

Request model for creating a JobScript entry from a template.

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**template_output_name_mapping** | **Dict[str, str]** | A mapping of template names to file names. The first element is the entrypoint, the others are optional support files. | 
**sbatch_params** | **List[str]** | SBATCH parameters to inject into the job_script | [optional] 
**param_dict** | **object** | Parameters to use when rendering the job_script jinja2 template | 

## Example

```python
from openapi_client.models.render_from_template_request import RenderFromTemplateRequest

# TODO update the JSON string below
json = "{}"
# create an instance of RenderFromTemplateRequest from a JSON string
render_from_template_request_instance = RenderFromTemplateRequest.from_json(json)
# print the JSON string representation of the object
print RenderFromTemplateRequest.to_json()

# convert the object into a dict
render_from_template_request_dict = render_from_template_request_instance.to_dict()
# create an instance of RenderFromTemplateRequest from a dict
render_from_template_request_form_dict = render_from_template_request.from_dict(render_from_template_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


