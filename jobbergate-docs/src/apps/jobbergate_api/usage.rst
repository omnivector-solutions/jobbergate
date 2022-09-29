======================
 Using Jobbergate API
======================

The Jobbergate API is intended to be consumed by automated processes or other applications. These include
the Jobbergate CLI and Jobbergate Agent, but it may serve any number of other applications.

The Jobbergate API is a standard RESTful API that uses HTTP for commuinication.


Getting an Auth Token
---------------------

Before the Jobbergate API can be consumed, you must first secure an access token that authenticates the requests
and grants authorization based on your user's permissions.

Jobbergate API's auth is provided by a connected OIDC service. You may make calls directly to this service from your
app to secure an auth token, but the easiest way to procure a token is through the Jobbergate CLI. See the
"Logging In" section on the `CLI usage`_ page


Querying the API
----------------

Once you have an auth token, you can interact with any of the Jobbergate API endpoints. To see a complete list of the
endpoints and information about the request and response schemas, you can visit the `swagger`_ page.

For requests made through a command-line tool or API testing tool like `Postman`_, you must include the auth token in
the ``Authorization`` header of requests with a prefix like ``Bearer token-text-here``.


Query Examples
--------------

For these examples:

* Auth token value will be "XXXXXXXX"
* Jobbergate API base URL is "http://jobbergate.local:8000/jobbergate"
* Goal is to fetch the list of all available Job Scripts


`curl`_
.......

From a linux terminal, we can use the `curl`_ command to make a request to an API quite easily:

.. code-block:: console

   curl --header "Authorization: Bearer XXXXXXXX"  http://jobbergate.local/jobbergate/job-scripts

   {"results":[{"id":1,"created_at":"2022-09-09T21:34:16.889289","updated_at":"2022-09-09T21:34:16.889289","job_script_name":"test script","job_script_description":null,"job_script_owner_email":"local-user@jobbergate.local","application_id":1}],"pagination":{"total":1,"start":null,"limit":null}}

To see the result more clearly, you can use a tool like ``jq`` to format the JSON response::

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


Python and httpx
----------------

In python, we can use the `httpx`_ package to easily send requests to and process responses from an API:

.. code-block:: python

   import json
   import httpx


   token = "XXXXXXXX"

   resp = httpx.get(
       "http://localhost:8000/jobbergate/job-scripts",
       headers=dict(Authorization=f"Bearer {token}"),
   )

   print(json.dumps(resp.json(), indent=2))

The script will print out results like this::

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




.. _`CLI usage`: ../jobbergate_cli/usage.rst
.. _`swagger`: https://armada-k8s.staging.omnivector.solutions/jobbergate/docs>
.. _`postman`: https://www.postman.com/
.. _`curl`: https://man7.org/linux/man-pages/man1/curl.1.html
.. _`httpx`: https://www.python-httpx.org/
