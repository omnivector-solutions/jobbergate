# Jobbergate API Overview

The [Jobbergate API](https://github.com/omnivector-solutions/jobbergate/jobbergate-api) is a RESTful API that functions
as the Jobbergate platform's backbone. It offers access to the platform's data for various components, including the
Jobbergate CLI, agent, and any other interfaces requiring interaction with Jobbergate assets.

The API's endpoints are secured via OpenID Connect, and they require a valid auth token that is created when a user logs
into the system.


# Usage

The Jobbergate API is a standard RESTful API. It can be accessed vi a command-line tool like
[Curl](https://man7.org/linux/man-pages/man1/curl.1.html) or API testing tool like [Postman](https://www.postman.com/).


## Getting an Auth Token

To use the Jobbergate API, you need to obtain an access token first. This token both authenticates your requests and
provides authorization according to your user's rights.

The authentication for Jobbergate API is managed by an affiliated OIDC service. While it's possible to directly
interface with this service from your application to get an authentication token, the simplest method is via the
Jobbergate CLI. Refer to the "Logging In" segment on the [CLI usage](./jobbergate_cli.md#usage) page.


## Querying the API

Once you have an auth token, you can interact with any of the Jobbergate API endpoints. The complete set of endpoints,
parameters, and constraints are available through swagger documentation under `jobbergate/docs` wherever the API is
deployed.

For all requests made to secured endpoints, you must include the auth token in the `Authorization` header of your
requests with a "Bearer" prefix.


## Query Examples

To demonstrate how to use the API, the following examples will show how to fetch a list of all available Job Scripts.

For these examples:

 - The auth token will be "XXXXXXXX"
 - The Jobbergate API is deployed at "http://jobbergate.local"


### curl

From a linux terminal, you can use the [curl](https://man7.org/linux/man-pages/man1/curl.1.html) command to make a
request to the API:

```shell
curl --header "Authorization: Bearer XXXXXXXX"  http://jobbergate.local/jobbergate/job-scripts
```

The output of the above command should look something like:
```
{"results":[{"id":1,"created_at":"2022-09-09T21:34:16.889289","updated_at":"2022-09-09T21:34:16.889289","job_script_name":"test script","job_script_description":null,"job_script_owner_email":"local-user@jobbergate.local","application_id":1}],"pagination":{"total":1,"start":null,"limit":null}}
```

To see the result more clearly, you can use a tool like `jq` to format the JSON response:

```json
{
  "results": [
    {
      "id": 1,
      "created_at": "2022-09-09T21:34:16.889289",
      "updated_at": "2022-09-09T21:34:16.889289",
      "job_script_name": "test script",
      "job_script_description": null,
      "job_script_owner_email": "local-user@jobbergate.local",
      "application_id": 1
    }
  ],
  "pagination": {
    "total": 1,
    "start": null,
    "limit": null
  }
}
```


### Python and httpx

In python, you can use the [httpx](https://www.python-httpx.org/) package to send requests to and process responses from
the API:

```python
import json
import httpx


token = "XXXXXXXX"

resp = httpx.get(
    "http://localhost:8000/jobbergate/job-scripts",
    headers=dict(Authorization=f"Bearer {token}"),
)

print(json.dumps(resp.json(), indent=2))
```


The script will print out results like this:

```json
{
  "results": [
    {
      "id": 1,
      "created_at": "2022-09-09T21:34:16.889289",
      "updated_at": "2022-09-09T21:34:16.889289",
      "job_script_name": "foo",
      "job_script_description": null,
      "job_script_owner_email": "local-user@jobbergate.local",
      "application_id": 1
    }
  ],
  "pagination": {
    "total": 1,
    "start": null,
    "limit": null
  }
}
```
