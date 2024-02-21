# openapi_client.JobScriptTemplatesApi

All URIs are relative to *http://localhost:8000/jobbergate*

Method | HTTP request | Description
------------- | ------------- | -------------
[**job_script_template_clone_job_script_templates_clone_id_or_identifier_post**](JobScriptTemplatesApi.md#job_script_template_clone_job_script_templates_clone_id_or_identifier_post) | **POST** /job-script-templates/clone/{id_or_identifier} | Job Script Template Clone
[**job_script_template_create_job_script_templates_post**](JobScriptTemplatesApi.md#job_script_template_create_job_script_templates_post) | **POST** /job-script-templates | Job Script Template Create
[**job_script_template_delete_file_job_script_templates_id_or_identifier_upload_template_file_name_delete**](JobScriptTemplatesApi.md#job_script_template_delete_file_job_script_templates_id_or_identifier_upload_template_file_name_delete) | **DELETE** /job-script-templates/{id_or_identifier}/upload/template/{file_name} | Job Script Template Delete File
[**job_script_template_delete_job_script_templates_id_or_identifier_delete**](JobScriptTemplatesApi.md#job_script_template_delete_job_script_templates_id_or_identifier_delete) | **DELETE** /job-script-templates/{id_or_identifier} | Job Script Template Delete
[**job_script_template_garbage_collector_job_script_templates_upload_garbage_collector_delete**](JobScriptTemplatesApi.md#job_script_template_garbage_collector_job_script_templates_upload_garbage_collector_delete) | **DELETE** /job-script-templates/upload/garbage-collector | Job Script Template Garbage Collector
[**job_script_template_get_file_job_script_templates_id_or_identifier_upload_template_file_name_get**](JobScriptTemplatesApi.md#job_script_template_get_file_job_script_templates_id_or_identifier_upload_template_file_name_get) | **GET** /job-script-templates/{id_or_identifier}/upload/template/{file_name} | Job Script Template Get File
[**job_script_template_get_job_script_templates_id_or_identifier_get**](JobScriptTemplatesApi.md#job_script_template_get_job_script_templates_id_or_identifier_get) | **GET** /job-script-templates/{id_or_identifier} | Job Script Template Get
[**job_script_template_get_list_job_script_templates_get**](JobScriptTemplatesApi.md#job_script_template_get_list_job_script_templates_get) | **GET** /job-script-templates | Job Script Template Get List
[**job_script_template_update_job_script_templates_id_or_identifier_put**](JobScriptTemplatesApi.md#job_script_template_update_job_script_templates_id_or_identifier_put) | **PUT** /job-script-templates/{id_or_identifier} | Job Script Template Update
[**job_script_template_upload_file_job_script_templates_id_or_identifier_upload_template_file_type_put**](JobScriptTemplatesApi.md#job_script_template_upload_file_job_script_templates_id_or_identifier_upload_template_file_type_put) | **PUT** /job-script-templates/{id_or_identifier}/upload/template/{file_type} | Job Script Template Upload File
[**job_script_workflow_delete_file_job_script_templates_id_or_identifier_upload_workflow_delete**](JobScriptTemplatesApi.md#job_script_workflow_delete_file_job_script_templates_id_or_identifier_upload_workflow_delete) | **DELETE** /job-script-templates/{id_or_identifier}/upload/workflow | Job Script Workflow Delete File
[**job_script_workflow_get_file_job_script_templates_id_or_identifier_upload_workflow_get**](JobScriptTemplatesApi.md#job_script_workflow_get_file_job_script_templates_id_or_identifier_upload_workflow_get) | **GET** /job-script-templates/{id_or_identifier}/upload/workflow | Job Script Workflow Get File
[**job_script_workflow_upload_file_job_script_templates_id_or_identifier_upload_workflow_put**](JobScriptTemplatesApi.md#job_script_workflow_upload_file_job_script_templates_id_or_identifier_upload_workflow_put) | **PUT** /job-script-templates/{id_or_identifier}/upload/workflow | Job Script Workflow Upload File


# **job_script_template_clone_job_script_templates_clone_id_or_identifier_post**
> JobTemplateDetailedView job_script_template_clone_job_script_templates_clone_id_or_identifier_post(id_or_identifier, job_template_clone_request=job_template_clone_request)

Job Script Template Clone

Endpoint for cloning a job script template to a new entry owned by the user

### Example

* Api Key Authentication (TokenSecurity):
```python
import time
import os
import openapi_client
from openapi_client.models.job_template_clone_request import JobTemplateCloneRequest
from openapi_client.models.job_template_detailed_view import JobTemplateDetailedView
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost:8000/jobbergate
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost:8000/jobbergate"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: TokenSecurity
configuration.api_key['TokenSecurity'] = os.environ["API_KEY"]

# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['TokenSecurity'] = 'Bearer'

# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.JobScriptTemplatesApi(api_client)
    id_or_identifier = openapi_client.IdOrIdentifier() # IdOrIdentifier | 
    job_template_clone_request = openapi_client.JobTemplateCloneRequest() # JobTemplateCloneRequest |  (optional)

    try:
        # Job Script Template Clone
        api_response = api_instance.job_script_template_clone_job_script_templates_clone_id_or_identifier_post(id_or_identifier, job_template_clone_request=job_template_clone_request)
        print("The response of JobScriptTemplatesApi->job_script_template_clone_job_script_templates_clone_id_or_identifier_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobScriptTemplatesApi->job_script_template_clone_job_script_templates_clone_id_or_identifier_post: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id_or_identifier** | [**IdOrIdentifier**](.md)|  | 
 **job_template_clone_request** | [**JobTemplateCloneRequest**](JobTemplateCloneRequest.md)|  | [optional] 

### Return type

[**JobTemplateDetailedView**](JobTemplateDetailedView.md)

### Authorization

[TokenSecurity](../README.md#TokenSecurity)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**201** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **job_script_template_create_job_script_templates_post**
> JobTemplateDetailedView job_script_template_create_job_script_templates_post(job_template_create_request)

Job Script Template Create

Endpoint for job script template creation

### Example

* Api Key Authentication (TokenSecurity):
```python
import time
import os
import openapi_client
from openapi_client.models.job_template_create_request import JobTemplateCreateRequest
from openapi_client.models.job_template_detailed_view import JobTemplateDetailedView
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost:8000/jobbergate
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost:8000/jobbergate"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: TokenSecurity
configuration.api_key['TokenSecurity'] = os.environ["API_KEY"]

# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['TokenSecurity'] = 'Bearer'

# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.JobScriptTemplatesApi(api_client)
    job_template_create_request = openapi_client.JobTemplateCreateRequest() # JobTemplateCreateRequest | 

    try:
        # Job Script Template Create
        api_response = api_instance.job_script_template_create_job_script_templates_post(job_template_create_request)
        print("The response of JobScriptTemplatesApi->job_script_template_create_job_script_templates_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobScriptTemplatesApi->job_script_template_create_job_script_templates_post: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **job_template_create_request** | [**JobTemplateCreateRequest**](JobTemplateCreateRequest.md)|  | 

### Return type

[**JobTemplateDetailedView**](JobTemplateDetailedView.md)

### Authorization

[TokenSecurity](../README.md#TokenSecurity)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**201** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **job_script_template_delete_file_job_script_templates_id_or_identifier_upload_template_file_name_delete**
> object job_script_template_delete_file_job_script_templates_id_or_identifier_upload_template_file_name_delete(id_or_identifier, file_name)

Job Script Template Delete File

Endpoint to delete a file to a job script template by id or identifier

### Example

* Api Key Authentication (TokenSecurity):
```python
import time
import os
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost:8000/jobbergate
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost:8000/jobbergate"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: TokenSecurity
configuration.api_key['TokenSecurity'] = os.environ["API_KEY"]

# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['TokenSecurity'] = 'Bearer'

# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.JobScriptTemplatesApi(api_client)
    id_or_identifier = openapi_client.IdOrIdentifier() # IdOrIdentifier | 
    file_name = 'file_name_example' # str | 

    try:
        # Job Script Template Delete File
        api_response = api_instance.job_script_template_delete_file_job_script_templates_id_or_identifier_upload_template_file_name_delete(id_or_identifier, file_name)
        print("The response of JobScriptTemplatesApi->job_script_template_delete_file_job_script_templates_id_or_identifier_upload_template_file_name_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobScriptTemplatesApi->job_script_template_delete_file_job_script_templates_id_or_identifier_upload_template_file_name_delete: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id_or_identifier** | [**IdOrIdentifier**](.md)|  | 
 **file_name** | **str**|  | 

### Return type

**object**

### Authorization

[TokenSecurity](../README.md#TokenSecurity)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **job_script_template_delete_job_script_templates_id_or_identifier_delete**
> job_script_template_delete_job_script_templates_id_or_identifier_delete(id_or_identifier)

Job Script Template Delete

Endpoint to delete a job script template by id or identifier

### Example

* Api Key Authentication (TokenSecurity):
```python
import time
import os
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost:8000/jobbergate
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost:8000/jobbergate"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: TokenSecurity
configuration.api_key['TokenSecurity'] = os.environ["API_KEY"]

# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['TokenSecurity'] = 'Bearer'

# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.JobScriptTemplatesApi(api_client)
    id_or_identifier = openapi_client.IdOrIdentifier() # IdOrIdentifier | 

    try:
        # Job Script Template Delete
        api_instance.job_script_template_delete_job_script_templates_id_or_identifier_delete(id_or_identifier)
    except Exception as e:
        print("Exception when calling JobScriptTemplatesApi->job_script_template_delete_job_script_templates_id_or_identifier_delete: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id_or_identifier** | [**IdOrIdentifier**](.md)|  | 

### Return type

void (empty response body)

### Authorization

[TokenSecurity](../README.md#TokenSecurity)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **job_script_template_garbage_collector_job_script_templates_upload_garbage_collector_delete**
> object job_script_template_garbage_collector_job_script_templates_upload_garbage_collector_delete()

Job Script Template Garbage Collector

Endpoint to delete all unused files from the job script template file storage

### Example

* Api Key Authentication (TokenSecurity):
```python
import time
import os
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost:8000/jobbergate
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost:8000/jobbergate"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: TokenSecurity
configuration.api_key['TokenSecurity'] = os.environ["API_KEY"]

# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['TokenSecurity'] = 'Bearer'

# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.JobScriptTemplatesApi(api_client)

    try:
        # Job Script Template Garbage Collector
        api_response = api_instance.job_script_template_garbage_collector_job_script_templates_upload_garbage_collector_delete()
        print("The response of JobScriptTemplatesApi->job_script_template_garbage_collector_job_script_templates_upload_garbage_collector_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobScriptTemplatesApi->job_script_template_garbage_collector_job_script_templates_upload_garbage_collector_delete: %s\n" % e)
```



### Parameters
This endpoint does not need any parameter.

### Return type

**object**

### Authorization

[TokenSecurity](../README.md#TokenSecurity)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**202** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **job_script_template_get_file_job_script_templates_id_or_identifier_upload_template_file_name_get**
> object job_script_template_get_file_job_script_templates_id_or_identifier_upload_template_file_name_get(id_or_identifier, file_name)

Job Script Template Get File

Endpoint to get a file from a job script template by id or identifier

### Example

* Api Key Authentication (TokenSecurity):
```python
import time
import os
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost:8000/jobbergate
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost:8000/jobbergate"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: TokenSecurity
configuration.api_key['TokenSecurity'] = os.environ["API_KEY"]

# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['TokenSecurity'] = 'Bearer'

# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.JobScriptTemplatesApi(api_client)
    id_or_identifier = openapi_client.IdOrIdentifier() # IdOrIdentifier | 
    file_name = 'file_name_example' # str | 

    try:
        # Job Script Template Get File
        api_response = api_instance.job_script_template_get_file_job_script_templates_id_or_identifier_upload_template_file_name_get(id_or_identifier, file_name)
        print("The response of JobScriptTemplatesApi->job_script_template_get_file_job_script_templates_id_or_identifier_upload_template_file_name_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobScriptTemplatesApi->job_script_template_get_file_job_script_templates_id_or_identifier_upload_template_file_name_get: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id_or_identifier** | [**IdOrIdentifier**](.md)|  | 
 **file_name** | **str**|  | 

### Return type

**object**

### Authorization

[TokenSecurity](../README.md#TokenSecurity)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **job_script_template_get_job_script_templates_id_or_identifier_get**
> JobTemplateDetailedView job_script_template_get_job_script_templates_id_or_identifier_get(id_or_identifier)

Job Script Template Get

Endpoint to return a job script template by its id or identifier

### Example

* Api Key Authentication (TokenSecurity):
```python
import time
import os
import openapi_client
from openapi_client.models.job_template_detailed_view import JobTemplateDetailedView
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost:8000/jobbergate
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost:8000/jobbergate"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: TokenSecurity
configuration.api_key['TokenSecurity'] = os.environ["API_KEY"]

# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['TokenSecurity'] = 'Bearer'

# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.JobScriptTemplatesApi(api_client)
    id_or_identifier = openapi_client.IdOrIdentifier() # IdOrIdentifier | 

    try:
        # Job Script Template Get
        api_response = api_instance.job_script_template_get_job_script_templates_id_or_identifier_get(id_or_identifier)
        print("The response of JobScriptTemplatesApi->job_script_template_get_job_script_templates_id_or_identifier_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobScriptTemplatesApi->job_script_template_get_job_script_templates_id_or_identifier_get: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id_or_identifier** | [**IdOrIdentifier**](.md)|  | 

### Return type

[**JobTemplateDetailedView**](JobTemplateDetailedView.md)

### Authorization

[TokenSecurity](../README.md#TokenSecurity)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **job_script_template_get_list_job_script_templates_get**
> PageJobTemplateListView job_script_template_get_list_job_script_templates_get(include_null_identifier=include_null_identifier, sort_ascending=sort_ascending, user_only=user_only, search=search, sort_field=sort_field, include_archived=include_archived, include_parent=include_parent, page=page, size=size)

Job Script Template Get List

Endpoint to return a list of job script templates

### Example

* Api Key Authentication (TokenSecurity):
```python
import time
import os
import openapi_client
from openapi_client.models.page_job_template_list_view import PageJobTemplateListView
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost:8000/jobbergate
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost:8000/jobbergate"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: TokenSecurity
configuration.api_key['TokenSecurity'] = os.environ["API_KEY"]

# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['TokenSecurity'] = 'Bearer'

# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.JobScriptTemplatesApi(api_client)
    include_null_identifier = False # bool |  (optional) (default to False)
    sort_ascending = True # bool |  (optional) (default to True)
    user_only = False # bool |  (optional) (default to False)
    search = 'search_example' # str |  (optional)
    sort_field = 'sort_field_example' # str |  (optional)
    include_archived = False # bool |  (optional) (default to False)
    include_parent = False # bool |  (optional) (default to False)
    page = 1 # int |  (optional) (default to 1)
    size = 50 # int |  (optional) (default to 50)

    try:
        # Job Script Template Get List
        api_response = api_instance.job_script_template_get_list_job_script_templates_get(include_null_identifier=include_null_identifier, sort_ascending=sort_ascending, user_only=user_only, search=search, sort_field=sort_field, include_archived=include_archived, include_parent=include_parent, page=page, size=size)
        print("The response of JobScriptTemplatesApi->job_script_template_get_list_job_script_templates_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobScriptTemplatesApi->job_script_template_get_list_job_script_templates_get: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **include_null_identifier** | **bool**|  | [optional] [default to False]
 **sort_ascending** | **bool**|  | [optional] [default to True]
 **user_only** | **bool**|  | [optional] [default to False]
 **search** | **str**|  | [optional] 
 **sort_field** | **str**|  | [optional] 
 **include_archived** | **bool**|  | [optional] [default to False]
 **include_parent** | **bool**|  | [optional] [default to False]
 **page** | **int**|  | [optional] [default to 1]
 **size** | **int**|  | [optional] [default to 50]

### Return type

[**PageJobTemplateListView**](PageJobTemplateListView.md)

### Authorization

[TokenSecurity](../README.md#TokenSecurity)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **job_script_template_update_job_script_templates_id_or_identifier_put**
> JobTemplateDetailedView job_script_template_update_job_script_templates_id_or_identifier_put(id_or_identifier, job_template_update_request)

Job Script Template Update

Endpoint to update a job script template by id or identifier

### Example

* Api Key Authentication (TokenSecurity):
```python
import time
import os
import openapi_client
from openapi_client.models.job_template_detailed_view import JobTemplateDetailedView
from openapi_client.models.job_template_update_request import JobTemplateUpdateRequest
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost:8000/jobbergate
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost:8000/jobbergate"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: TokenSecurity
configuration.api_key['TokenSecurity'] = os.environ["API_KEY"]

# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['TokenSecurity'] = 'Bearer'

# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.JobScriptTemplatesApi(api_client)
    id_or_identifier = openapi_client.IdOrIdentifier() # IdOrIdentifier | 
    job_template_update_request = openapi_client.JobTemplateUpdateRequest() # JobTemplateUpdateRequest | 

    try:
        # Job Script Template Update
        api_response = api_instance.job_script_template_update_job_script_templates_id_or_identifier_put(id_or_identifier, job_template_update_request)
        print("The response of JobScriptTemplatesApi->job_script_template_update_job_script_templates_id_or_identifier_put:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobScriptTemplatesApi->job_script_template_update_job_script_templates_id_or_identifier_put: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id_or_identifier** | [**IdOrIdentifier**](.md)|  | 
 **job_template_update_request** | [**JobTemplateUpdateRequest**](JobTemplateUpdateRequest.md)|  | 

### Return type

[**JobTemplateDetailedView**](JobTemplateDetailedView.md)

### Authorization

[TokenSecurity](../README.md#TokenSecurity)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **job_script_template_upload_file_job_script_templates_id_or_identifier_upload_template_file_type_put**
> TemplateFileDetailedView job_script_template_upload_file_job_script_templates_id_or_identifier_upload_template_file_type_put(id_or_identifier, file_type, upload_file)

Job Script Template Upload File

Endpoint to upload a file to a job script template by id or identifier

### Example

* Api Key Authentication (TokenSecurity):
```python
import time
import os
import openapi_client
from openapi_client.models.file_type import FileType
from openapi_client.models.template_file_detailed_view import TemplateFileDetailedView
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost:8000/jobbergate
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost:8000/jobbergate"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: TokenSecurity
configuration.api_key['TokenSecurity'] = os.environ["API_KEY"]

# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['TokenSecurity'] = 'Bearer'

# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.JobScriptTemplatesApi(api_client)
    id_or_identifier = openapi_client.IdOrIdentifier() # IdOrIdentifier | 
    file_type = openapi_client.FileType() # FileType | 
    upload_file = None # bytearray | File to upload

    try:
        # Job Script Template Upload File
        api_response = api_instance.job_script_template_upload_file_job_script_templates_id_or_identifier_upload_template_file_type_put(id_or_identifier, file_type, upload_file)
        print("The response of JobScriptTemplatesApi->job_script_template_upload_file_job_script_templates_id_or_identifier_upload_template_file_type_put:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobScriptTemplatesApi->job_script_template_upload_file_job_script_templates_id_or_identifier_upload_template_file_type_put: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id_or_identifier** | [**IdOrIdentifier**](.md)|  | 
 **file_type** | [**FileType**](.md)|  | 
 **upload_file** | **bytearray**| File to upload | 

### Return type

[**TemplateFileDetailedView**](TemplateFileDetailedView.md)

### Authorization

[TokenSecurity](../README.md#TokenSecurity)

### HTTP request headers

 - **Content-Type**: multipart/form-data
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **job_script_workflow_delete_file_job_script_templates_id_or_identifier_upload_workflow_delete**
> object job_script_workflow_delete_file_job_script_templates_id_or_identifier_upload_workflow_delete(id_or_identifier)

Job Script Workflow Delete File

Endpoint to delete a workflow file from a job script template by id or identifier

### Example

* Api Key Authentication (TokenSecurity):
```python
import time
import os
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost:8000/jobbergate
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost:8000/jobbergate"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: TokenSecurity
configuration.api_key['TokenSecurity'] = os.environ["API_KEY"]

# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['TokenSecurity'] = 'Bearer'

# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.JobScriptTemplatesApi(api_client)
    id_or_identifier = openapi_client.IdOrIdentifier() # IdOrIdentifier | 

    try:
        # Job Script Workflow Delete File
        api_response = api_instance.job_script_workflow_delete_file_job_script_templates_id_or_identifier_upload_workflow_delete(id_or_identifier)
        print("The response of JobScriptTemplatesApi->job_script_workflow_delete_file_job_script_templates_id_or_identifier_upload_workflow_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobScriptTemplatesApi->job_script_workflow_delete_file_job_script_templates_id_or_identifier_upload_workflow_delete: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id_or_identifier** | [**IdOrIdentifier**](.md)|  | 

### Return type

**object**

### Authorization

[TokenSecurity](../README.md#TokenSecurity)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **job_script_workflow_get_file_job_script_templates_id_or_identifier_upload_workflow_get**
> object job_script_workflow_get_file_job_script_templates_id_or_identifier_upload_workflow_get(id_or_identifier)

Job Script Workflow Get File

Endpoint to get a workflow file from a job script template by id or identifier

### Example

* Api Key Authentication (TokenSecurity):
```python
import time
import os
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost:8000/jobbergate
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost:8000/jobbergate"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: TokenSecurity
configuration.api_key['TokenSecurity'] = os.environ["API_KEY"]

# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['TokenSecurity'] = 'Bearer'

# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.JobScriptTemplatesApi(api_client)
    id_or_identifier = openapi_client.IdOrIdentifier() # IdOrIdentifier | 

    try:
        # Job Script Workflow Get File
        api_response = api_instance.job_script_workflow_get_file_job_script_templates_id_or_identifier_upload_workflow_get(id_or_identifier)
        print("The response of JobScriptTemplatesApi->job_script_workflow_get_file_job_script_templates_id_or_identifier_upload_workflow_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobScriptTemplatesApi->job_script_workflow_get_file_job_script_templates_id_or_identifier_upload_workflow_get: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id_or_identifier** | [**IdOrIdentifier**](.md)|  | 

### Return type

**object**

### Authorization

[TokenSecurity](../README.md#TokenSecurity)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **job_script_workflow_upload_file_job_script_templates_id_or_identifier_upload_workflow_put**
> WorkflowFileDetailedView job_script_workflow_upload_file_job_script_templates_id_or_identifier_upload_workflow_put(id_or_identifier, upload_file, runtime_config=runtime_config)

Job Script Workflow Upload File

Endpoint to upload a file to a job script template by id or identifier

### Example

* Api Key Authentication (TokenSecurity):
```python
import time
import os
import openapi_client
from openapi_client.models.workflow_file_detailed_view import WorkflowFileDetailedView
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost:8000/jobbergate
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost:8000/jobbergate"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: TokenSecurity
configuration.api_key['TokenSecurity'] = os.environ["API_KEY"]

# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['TokenSecurity'] = 'Bearer'

# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.JobScriptTemplatesApi(api_client)
    id_or_identifier = openapi_client.IdOrIdentifier() # IdOrIdentifier | 
    upload_file = None # bytearray | File to upload
    runtime_config = None # object | Runtime configuration is optional when the workflow file already exists (optional)

    try:
        # Job Script Workflow Upload File
        api_response = api_instance.job_script_workflow_upload_file_job_script_templates_id_or_identifier_upload_workflow_put(id_or_identifier, upload_file, runtime_config=runtime_config)
        print("The response of JobScriptTemplatesApi->job_script_workflow_upload_file_job_script_templates_id_or_identifier_upload_workflow_put:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobScriptTemplatesApi->job_script_workflow_upload_file_job_script_templates_id_or_identifier_upload_workflow_put: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id_or_identifier** | [**IdOrIdentifier**](.md)|  | 
 **upload_file** | **bytearray**| File to upload | 
 **runtime_config** | [**object**](object.md)| Runtime configuration is optional when the workflow file already exists | [optional] 

### Return type

[**WorkflowFileDetailedView**](WorkflowFileDetailedView.md)

### Authorization

[TokenSecurity](../README.md#TokenSecurity)

### HTTP request headers

 - **Content-Type**: multipart/form-data
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

