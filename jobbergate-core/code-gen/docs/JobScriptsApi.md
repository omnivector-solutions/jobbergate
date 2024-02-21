# openapi_client.JobScriptsApi

All URIs are relative to *http://localhost:8000/jobbergate*

Method | HTTP request | Description
------------- | ------------- | -------------
[**job_script_auto_clean_unused_entries_job_scripts_clean_unused_entries_delete**](JobScriptsApi.md#job_script_auto_clean_unused_entries_job_scripts_clean_unused_entries_delete) | **DELETE** /job-scripts/clean-unused-entries | Job Script Auto Clean Unused Entries
[**job_script_clone_job_scripts_clone_id_post**](JobScriptsApi.md#job_script_clone_job_scripts_clone_id_post) | **POST** /job-scripts/clone/{id} | Job Script Clone
[**job_script_create_from_template_job_scripts_render_from_template_id_or_identifier_post**](JobScriptsApi.md#job_script_create_from_template_job_scripts_render_from_template_id_or_identifier_post) | **POST** /job-scripts/render-from-template/{id_or_identifier} | Job Script Create From Template
[**job_script_create_job_scripts_post**](JobScriptsApi.md#job_script_create_job_scripts_post) | **POST** /job-scripts | Job Script Create
[**job_script_delete_file_job_scripts_id_upload_file_name_delete**](JobScriptsApi.md#job_script_delete_file_job_scripts_id_upload_file_name_delete) | **DELETE** /job-scripts/{id}/upload/{file_name} | Job Script Delete File
[**job_script_delete_job_scripts_id_delete**](JobScriptsApi.md#job_script_delete_job_scripts_id_delete) | **DELETE** /job-scripts/{id} | Job Script Delete
[**job_script_garbage_collector_job_scripts_upload_garbage_collector_delete**](JobScriptsApi.md#job_script_garbage_collector_job_scripts_upload_garbage_collector_delete) | **DELETE** /job-scripts/upload/garbage-collector | Job Script Garbage Collector
[**job_script_get_file_job_scripts_id_upload_file_name_get**](JobScriptsApi.md#job_script_get_file_job_scripts_id_upload_file_name_get) | **GET** /job-scripts/{id}/upload/{file_name} | Job Script Get File
[**job_script_get_job_scripts_id_get**](JobScriptsApi.md#job_script_get_job_scripts_id_get) | **GET** /job-scripts/{id} | Job Script Get
[**job_script_get_list_job_scripts_get**](JobScriptsApi.md#job_script_get_list_job_scripts_get) | **GET** /job-scripts | Job Script Get List
[**job_script_update_job_scripts_id_put**](JobScriptsApi.md#job_script_update_job_scripts_id_put) | **PUT** /job-scripts/{id} | Job Script Update
[**job_script_upload_file_job_scripts_id_upload_file_type_put**](JobScriptsApi.md#job_script_upload_file_job_scripts_id_upload_file_type_put) | **PUT** /job-scripts/{id}/upload/{file_type} | Job Script Upload File


# **job_script_auto_clean_unused_entries_job_scripts_clean_unused_entries_delete**
> object job_script_auto_clean_unused_entries_job_scripts_clean_unused_entries_delete()

Job Script Auto Clean Unused Entries

Endpoint to automatically clean unused job scripts depending on a threshold

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
    api_instance = openapi_client.JobScriptsApi(api_client)

    try:
        # Job Script Auto Clean Unused Entries
        api_response = api_instance.job_script_auto_clean_unused_entries_job_scripts_clean_unused_entries_delete()
        print("The response of JobScriptsApi->job_script_auto_clean_unused_entries_job_scripts_clean_unused_entries_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobScriptsApi->job_script_auto_clean_unused_entries_job_scripts_clean_unused_entries_delete: %s\n" % e)
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

# **job_script_clone_job_scripts_clone_id_post**
> JobScriptDetailedView job_script_clone_job_scripts_clone_id_post(id, job_script_clone_request=job_script_clone_request)

Job Script Clone

Endpoint for cloning a job script to a new entry owned by the user

### Example

* Api Key Authentication (TokenSecurity):
```python
import time
import os
import openapi_client
from openapi_client.models.job_script_clone_request import JobScriptCloneRequest
from openapi_client.models.job_script_detailed_view import JobScriptDetailedView
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
    api_instance = openapi_client.JobScriptsApi(api_client)
    id = 56 # int | 
    job_script_clone_request = openapi_client.JobScriptCloneRequest() # JobScriptCloneRequest |  (optional)

    try:
        # Job Script Clone
        api_response = api_instance.job_script_clone_job_scripts_clone_id_post(id, job_script_clone_request=job_script_clone_request)
        print("The response of JobScriptsApi->job_script_clone_job_scripts_clone_id_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobScriptsApi->job_script_clone_job_scripts_clone_id_post: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id** | **int**|  | 
 **job_script_clone_request** | [**JobScriptCloneRequest**](JobScriptCloneRequest.md)|  | [optional] 

### Return type

[**JobScriptDetailedView**](JobScriptDetailedView.md)

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

# **job_script_create_from_template_job_scripts_render_from_template_id_or_identifier_post**
> JobScriptDetailedView job_script_create_from_template_job_scripts_render_from_template_id_or_identifier_post(id_or_identifier, body_job_script_create_from_template_job_scripts_render_from_template_id_or_identifier_post)

Job Script Create From Template

Endpoint for job script creation

### Example

* Api Key Authentication (TokenSecurity):
```python
import time
import os
import openapi_client
from openapi_client.models.body_job_script_create_from_template_job_scripts_render_from_template_id_or_identifier_post import BodyJobScriptCreateFromTemplateJobScriptsRenderFromTemplateIdOrIdentifierPost
from openapi_client.models.job_script_detailed_view import JobScriptDetailedView
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
    api_instance = openapi_client.JobScriptsApi(api_client)
    id_or_identifier = openapi_client.IdOrIdentifier() # IdOrIdentifier | 
    body_job_script_create_from_template_job_scripts_render_from_template_id_or_identifier_post = openapi_client.BodyJobScriptCreateFromTemplateJobScriptsRenderFromTemplateIdOrIdentifierPost() # BodyJobScriptCreateFromTemplateJobScriptsRenderFromTemplateIdOrIdentifierPost | 

    try:
        # Job Script Create From Template
        api_response = api_instance.job_script_create_from_template_job_scripts_render_from_template_id_or_identifier_post(id_or_identifier, body_job_script_create_from_template_job_scripts_render_from_template_id_or_identifier_post)
        print("The response of JobScriptsApi->job_script_create_from_template_job_scripts_render_from_template_id_or_identifier_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobScriptsApi->job_script_create_from_template_job_scripts_render_from_template_id_or_identifier_post: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id_or_identifier** | [**IdOrIdentifier**](.md)|  | 
 **body_job_script_create_from_template_job_scripts_render_from_template_id_or_identifier_post** | [**BodyJobScriptCreateFromTemplateJobScriptsRenderFromTemplateIdOrIdentifierPost**](BodyJobScriptCreateFromTemplateJobScriptsRenderFromTemplateIdOrIdentifierPost.md)|  | 

### Return type

[**JobScriptDetailedView**](JobScriptDetailedView.md)

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

# **job_script_create_job_scripts_post**
> JobScriptDetailedView job_script_create_job_scripts_post(job_script_create_request)

Job Script Create

Endpoint for creating a stand alone job script. Use file upload to add files.

### Example

* Api Key Authentication (TokenSecurity):
```python
import time
import os
import openapi_client
from openapi_client.models.job_script_create_request import JobScriptCreateRequest
from openapi_client.models.job_script_detailed_view import JobScriptDetailedView
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
    api_instance = openapi_client.JobScriptsApi(api_client)
    job_script_create_request = openapi_client.JobScriptCreateRequest() # JobScriptCreateRequest | 

    try:
        # Job Script Create
        api_response = api_instance.job_script_create_job_scripts_post(job_script_create_request)
        print("The response of JobScriptsApi->job_script_create_job_scripts_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobScriptsApi->job_script_create_job_scripts_post: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **job_script_create_request** | [**JobScriptCreateRequest**](JobScriptCreateRequest.md)|  | 

### Return type

[**JobScriptDetailedView**](JobScriptDetailedView.md)

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

# **job_script_delete_file_job_scripts_id_upload_file_name_delete**
> object job_script_delete_file_job_scripts_id_upload_file_name_delete(id, file_name)

Job Script Delete File

Endpoint to delete a file from a job script

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
    api_instance = openapi_client.JobScriptsApi(api_client)
    id = 56 # int | 
    file_name = 'file_name_example' # str | 

    try:
        # Job Script Delete File
        api_response = api_instance.job_script_delete_file_job_scripts_id_upload_file_name_delete(id, file_name)
        print("The response of JobScriptsApi->job_script_delete_file_job_scripts_id_upload_file_name_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobScriptsApi->job_script_delete_file_job_scripts_id_upload_file_name_delete: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id** | **int**|  | 
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

# **job_script_delete_job_scripts_id_delete**
> job_script_delete_job_scripts_id_delete(id)

Job Script Delete

Endpoint to delete a job script by id

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
    api_instance = openapi_client.JobScriptsApi(api_client)
    id = 56 # int | 

    try:
        # Job Script Delete
        api_instance.job_script_delete_job_scripts_id_delete(id)
    except Exception as e:
        print("Exception when calling JobScriptsApi->job_script_delete_job_scripts_id_delete: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id** | **int**|  | 

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

# **job_script_garbage_collector_job_scripts_upload_garbage_collector_delete**
> object job_script_garbage_collector_job_scripts_upload_garbage_collector_delete()

Job Script Garbage Collector

Endpoint to delete all unused files from the job script file storage

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
    api_instance = openapi_client.JobScriptsApi(api_client)

    try:
        # Job Script Garbage Collector
        api_response = api_instance.job_script_garbage_collector_job_scripts_upload_garbage_collector_delete()
        print("The response of JobScriptsApi->job_script_garbage_collector_job_scripts_upload_garbage_collector_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobScriptsApi->job_script_garbage_collector_job_scripts_upload_garbage_collector_delete: %s\n" % e)
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

# **job_script_get_file_job_scripts_id_upload_file_name_get**
> object job_script_get_file_job_scripts_id_upload_file_name_get(id, file_name)

Job Script Get File

Endpoint to get a file from a job script

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
    api_instance = openapi_client.JobScriptsApi(api_client)
    id = 56 # int | 
    file_name = 'file_name_example' # str | 

    try:
        # Job Script Get File
        api_response = api_instance.job_script_get_file_job_scripts_id_upload_file_name_get(id, file_name)
        print("The response of JobScriptsApi->job_script_get_file_job_scripts_id_upload_file_name_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobScriptsApi->job_script_get_file_job_scripts_id_upload_file_name_get: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id** | **int**|  | 
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

# **job_script_get_job_scripts_id_get**
> JobScriptDetailedView job_script_get_job_scripts_id_get(id)

Job Script Get

Endpoint to return a job script by its id

### Example

* Api Key Authentication (TokenSecurity):
```python
import time
import os
import openapi_client
from openapi_client.models.job_script_detailed_view import JobScriptDetailedView
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
    api_instance = openapi_client.JobScriptsApi(api_client)
    id = 56 # int | 

    try:
        # Job Script Get
        api_response = api_instance.job_script_get_job_scripts_id_get(id)
        print("The response of JobScriptsApi->job_script_get_job_scripts_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobScriptsApi->job_script_get_job_scripts_id_get: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id** | **int**|  | 

### Return type

[**JobScriptDetailedView**](JobScriptDetailedView.md)

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

# **job_script_get_list_job_scripts_get**
> PageJobScriptListView job_script_get_list_job_scripts_get(from_job_script_template_id=from_job_script_template_id, sort_ascending=sort_ascending, user_only=user_only, search=search, sort_field=sort_field, include_archived=include_archived, include_parent=include_parent, page=page, size=size)

Job Script Get List

Endpoint to return a list of job scripts

### Example

* Api Key Authentication (TokenSecurity):
```python
import time
import os
import openapi_client
from openapi_client.models.page_job_script_list_view import PageJobScriptListView
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
    api_instance = openapi_client.JobScriptsApi(api_client)
    from_job_script_template_id = 56 # int | Filter job-scripts by the job-script-template-id they were created from. (optional)
    sort_ascending = True # bool |  (optional) (default to True)
    user_only = False # bool |  (optional) (default to False)
    search = 'search_example' # str |  (optional)
    sort_field = 'sort_field_example' # str |  (optional)
    include_archived = False # bool |  (optional) (default to False)
    include_parent = False # bool |  (optional) (default to False)
    page = 1 # int |  (optional) (default to 1)
    size = 50 # int |  (optional) (default to 50)

    try:
        # Job Script Get List
        api_response = api_instance.job_script_get_list_job_scripts_get(from_job_script_template_id=from_job_script_template_id, sort_ascending=sort_ascending, user_only=user_only, search=search, sort_field=sort_field, include_archived=include_archived, include_parent=include_parent, page=page, size=size)
        print("The response of JobScriptsApi->job_script_get_list_job_scripts_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobScriptsApi->job_script_get_list_job_scripts_get: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **from_job_script_template_id** | **int**| Filter job-scripts by the job-script-template-id they were created from. | [optional] 
 **sort_ascending** | **bool**|  | [optional] [default to True]
 **user_only** | **bool**|  | [optional] [default to False]
 **search** | **str**|  | [optional] 
 **sort_field** | **str**|  | [optional] 
 **include_archived** | **bool**|  | [optional] [default to False]
 **include_parent** | **bool**|  | [optional] [default to False]
 **page** | **int**|  | [optional] [default to 1]
 **size** | **int**|  | [optional] [default to 50]

### Return type

[**PageJobScriptListView**](PageJobScriptListView.md)

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

# **job_script_update_job_scripts_id_put**
> JobScriptListView job_script_update_job_scripts_id_put(id, job_script_update_request)

Job Script Update

Endpoint to update a job script by id

### Example

* Api Key Authentication (TokenSecurity):
```python
import time
import os
import openapi_client
from openapi_client.models.job_script_list_view import JobScriptListView
from openapi_client.models.job_script_update_request import JobScriptUpdateRequest
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
    api_instance = openapi_client.JobScriptsApi(api_client)
    id = 56 # int | 
    job_script_update_request = openapi_client.JobScriptUpdateRequest() # JobScriptUpdateRequest | 

    try:
        # Job Script Update
        api_response = api_instance.job_script_update_job_scripts_id_put(id, job_script_update_request)
        print("The response of JobScriptsApi->job_script_update_job_scripts_id_put:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobScriptsApi->job_script_update_job_scripts_id_put: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id** | **int**|  | 
 **job_script_update_request** | [**JobScriptUpdateRequest**](JobScriptUpdateRequest.md)|  | 

### Return type

[**JobScriptListView**](JobScriptListView.md)

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

# **job_script_upload_file_job_scripts_id_upload_file_type_put**
> object job_script_upload_file_job_scripts_id_upload_file_type_put(id, file_type, upload_file)

Job Script Upload File

Endpoint to upload a file to a job script file

### Example

* Api Key Authentication (TokenSecurity):
```python
import time
import os
import openapi_client
from openapi_client.models.file_type import FileType
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
    api_instance = openapi_client.JobScriptsApi(api_client)
    id = 56 # int | 
    file_type = openapi_client.FileType() # FileType | 
    upload_file = None # bytearray | File to upload

    try:
        # Job Script Upload File
        api_response = api_instance.job_script_upload_file_job_scripts_id_upload_file_type_put(id, file_type, upload_file)
        print("The response of JobScriptsApi->job_script_upload_file_job_scripts_id_upload_file_type_put:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobScriptsApi->job_script_upload_file_job_scripts_id_upload_file_type_put: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id** | **int**|  | 
 **file_type** | [**FileType**](.md)|  | 
 **upload_file** | **bytearray**| File to upload | 

### Return type

**object**

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

