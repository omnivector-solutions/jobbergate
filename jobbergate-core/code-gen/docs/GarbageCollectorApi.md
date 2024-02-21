# openapi_client.GarbageCollectorApi

All URIs are relative to *http://localhost:8000/jobbergate*

Method | HTTP request | Description
------------- | ------------- | -------------
[**job_script_auto_clean_unused_entries_job_scripts_clean_unused_entries_delete**](GarbageCollectorApi.md#job_script_auto_clean_unused_entries_job_scripts_clean_unused_entries_delete) | **DELETE** /job-scripts/clean-unused-entries | Job Script Auto Clean Unused Entries
[**job_script_garbage_collector_job_scripts_upload_garbage_collector_delete**](GarbageCollectorApi.md#job_script_garbage_collector_job_scripts_upload_garbage_collector_delete) | **DELETE** /job-scripts/upload/garbage-collector | Job Script Garbage Collector
[**job_script_template_garbage_collector_job_script_templates_upload_garbage_collector_delete**](GarbageCollectorApi.md#job_script_template_garbage_collector_job_script_templates_upload_garbage_collector_delete) | **DELETE** /job-script-templates/upload/garbage-collector | Job Script Template Garbage Collector


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
    api_instance = openapi_client.GarbageCollectorApi(api_client)

    try:
        # Job Script Auto Clean Unused Entries
        api_response = api_instance.job_script_auto_clean_unused_entries_job_scripts_clean_unused_entries_delete()
        print("The response of GarbageCollectorApi->job_script_auto_clean_unused_entries_job_scripts_clean_unused_entries_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling GarbageCollectorApi->job_script_auto_clean_unused_entries_job_scripts_clean_unused_entries_delete: %s\n" % e)
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
    api_instance = openapi_client.GarbageCollectorApi(api_client)

    try:
        # Job Script Garbage Collector
        api_response = api_instance.job_script_garbage_collector_job_scripts_upload_garbage_collector_delete()
        print("The response of GarbageCollectorApi->job_script_garbage_collector_job_scripts_upload_garbage_collector_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling GarbageCollectorApi->job_script_garbage_collector_job_scripts_upload_garbage_collector_delete: %s\n" % e)
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
    api_instance = openapi_client.GarbageCollectorApi(api_client)

    try:
        # Job Script Template Garbage Collector
        api_response = api_instance.job_script_template_garbage_collector_job_script_templates_upload_garbage_collector_delete()
        print("The response of GarbageCollectorApi->job_script_template_garbage_collector_job_script_templates_upload_garbage_collector_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling GarbageCollectorApi->job_script_template_garbage_collector_job_script_templates_upload_garbage_collector_delete: %s\n" % e)
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

