# openapi_client.AgentApi

All URIs are relative to *http://localhost:8000/jobbergate*

Method | HTTP request | Description
------------- | ------------- | -------------
[**job_submission_agent_update_job_submissions_agent_id_put**](AgentApi.md#job_submission_agent_update_job_submissions_agent_id_put) | **PUT** /job-submissions/agent/{id} | Job Submission Agent Update
[**job_submissions_agent_active_job_submissions_agent_active_get**](AgentApi.md#job_submissions_agent_active_job_submissions_agent_active_get) | **GET** /job-submissions/agent/active | Job Submissions Agent Active
[**job_submissions_agent_pending_job_submissions_agent_pending_get**](AgentApi.md#job_submissions_agent_pending_job_submissions_agent_pending_get) | **GET** /job-submissions/agent/pending | Job Submissions Agent Pending
[**job_submissions_agent_rejected_job_submissions_agent_rejected_post**](AgentApi.md#job_submissions_agent_rejected_job_submissions_agent_rejected_post) | **POST** /job-submissions/agent/rejected | Job Submissions Agent Rejected
[**job_submissions_agent_submitted_job_submissions_agent_submitted_post**](AgentApi.md#job_submissions_agent_submitted_job_submissions_agent_submitted_post) | **POST** /job-submissions/agent/submitted | Job Submissions Agent Submitted


# **job_submission_agent_update_job_submissions_agent_id_put**
> object job_submission_agent_update_job_submissions_agent_id_put(id, job_submission_agent_update_request)

Job Submission Agent Update

Endpoint for an agent to update the status of a job_submission

### Example

* Api Key Authentication (TokenSecurity):
```python
import time
import os
import openapi_client
from openapi_client.models.job_submission_agent_update_request import JobSubmissionAgentUpdateRequest
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
    api_instance = openapi_client.AgentApi(api_client)
    id = 56 # int | 
    job_submission_agent_update_request = openapi_client.JobSubmissionAgentUpdateRequest() # JobSubmissionAgentUpdateRequest | 

    try:
        # Job Submission Agent Update
        api_response = api_instance.job_submission_agent_update_job_submissions_agent_id_put(id, job_submission_agent_update_request)
        print("The response of AgentApi->job_submission_agent_update_job_submissions_agent_id_put:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AgentApi->job_submission_agent_update_job_submissions_agent_id_put: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id** | **int**|  | 
 **job_submission_agent_update_request** | [**JobSubmissionAgentUpdateRequest**](JobSubmissionAgentUpdateRequest.md)|  | 

### Return type

**object**

### Authorization

[TokenSecurity](../README.md#TokenSecurity)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**202** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **job_submissions_agent_active_job_submissions_agent_active_get**
> PageActiveJobSubmission job_submissions_agent_active_job_submissions_agent_active_get(page=page, size=size)

Job Submissions Agent Active

Endpoint to list active job_submissions for the requesting client

### Example

* Api Key Authentication (TokenSecurity):
```python
import time
import os
import openapi_client
from openapi_client.models.page_active_job_submission import PageActiveJobSubmission
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
    api_instance = openapi_client.AgentApi(api_client)
    page = 1 # int |  (optional) (default to 1)
    size = 50 # int |  (optional) (default to 50)

    try:
        # Job Submissions Agent Active
        api_response = api_instance.job_submissions_agent_active_job_submissions_agent_active_get(page=page, size=size)
        print("The response of AgentApi->job_submissions_agent_active_job_submissions_agent_active_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AgentApi->job_submissions_agent_active_job_submissions_agent_active_get: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **page** | **int**|  | [optional] [default to 1]
 **size** | **int**|  | [optional] [default to 50]

### Return type

[**PageActiveJobSubmission**](PageActiveJobSubmission.md)

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

# **job_submissions_agent_pending_job_submissions_agent_pending_get**
> PagePendingJobSubmission job_submissions_agent_pending_job_submissions_agent_pending_get(page=page, size=size)

Job Submissions Agent Pending

Endpoint to list pending job_submissions for the requesting client

### Example

* Api Key Authentication (TokenSecurity):
```python
import time
import os
import openapi_client
from openapi_client.models.page_pending_job_submission import PagePendingJobSubmission
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
    api_instance = openapi_client.AgentApi(api_client)
    page = 1 # int |  (optional) (default to 1)
    size = 50 # int |  (optional) (default to 50)

    try:
        # Job Submissions Agent Pending
        api_response = api_instance.job_submissions_agent_pending_job_submissions_agent_pending_get(page=page, size=size)
        print("The response of AgentApi->job_submissions_agent_pending_job_submissions_agent_pending_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AgentApi->job_submissions_agent_pending_job_submissions_agent_pending_get: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **page** | **int**|  | [optional] [default to 1]
 **size** | **int**|  | [optional] [default to 50]

### Return type

[**PagePendingJobSubmission**](PagePendingJobSubmission.md)

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

# **job_submissions_agent_rejected_job_submissions_agent_rejected_post**
> object job_submissions_agent_rejected_job_submissions_agent_rejected_post(job_submission_agent_rejected_request)

Job Submissions Agent Rejected

Endpoint to report that a pending job_submission was rejected by Slurm

### Example

* Api Key Authentication (TokenSecurity):
```python
import time
import os
import openapi_client
from openapi_client.models.job_submission_agent_rejected_request import JobSubmissionAgentRejectedRequest
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
    api_instance = openapi_client.AgentApi(api_client)
    job_submission_agent_rejected_request = openapi_client.JobSubmissionAgentRejectedRequest() # JobSubmissionAgentRejectedRequest | 

    try:
        # Job Submissions Agent Rejected
        api_response = api_instance.job_submissions_agent_rejected_job_submissions_agent_rejected_post(job_submission_agent_rejected_request)
        print("The response of AgentApi->job_submissions_agent_rejected_job_submissions_agent_rejected_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AgentApi->job_submissions_agent_rejected_job_submissions_agent_rejected_post: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **job_submission_agent_rejected_request** | [**JobSubmissionAgentRejectedRequest**](JobSubmissionAgentRejectedRequest.md)|  | 

### Return type

**object**

### Authorization

[TokenSecurity](../README.md#TokenSecurity)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**202** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **job_submissions_agent_submitted_job_submissions_agent_submitted_post**
> object job_submissions_agent_submitted_job_submissions_agent_submitted_post(job_submission_agent_submitted_request)

Job Submissions Agent Submitted

Endpoint to report that a pending job_submission was submitted

### Example

* Api Key Authentication (TokenSecurity):
```python
import time
import os
import openapi_client
from openapi_client.models.job_submission_agent_submitted_request import JobSubmissionAgentSubmittedRequest
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
    api_instance = openapi_client.AgentApi(api_client)
    job_submission_agent_submitted_request = openapi_client.JobSubmissionAgentSubmittedRequest() # JobSubmissionAgentSubmittedRequest | 

    try:
        # Job Submissions Agent Submitted
        api_response = api_instance.job_submissions_agent_submitted_job_submissions_agent_submitted_post(job_submission_agent_submitted_request)
        print("The response of AgentApi->job_submissions_agent_submitted_job_submissions_agent_submitted_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AgentApi->job_submissions_agent_submitted_job_submissions_agent_submitted_post: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **job_submission_agent_submitted_request** | [**JobSubmissionAgentSubmittedRequest**](JobSubmissionAgentSubmittedRequest.md)|  | 

### Return type

**object**

### Authorization

[TokenSecurity](../README.md#TokenSecurity)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**202** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

