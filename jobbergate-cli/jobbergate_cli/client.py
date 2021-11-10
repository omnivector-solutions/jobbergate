"""
For troubleshooting and QA, turn on tracing of HTTP traffic through requests
"""
from http.client import HTTPConnection
import logging

# import locally so we can patch them when tracing
from requests import Session, delete, get, post, put


(
    get,
    post,
    put,
    delete,
)  # importable from here, we may patch them out if debugging is turned on


urllib3_logger = logging.getLogger("requests.packages.urllib3")


DEFAULT_MAX_BYTES_DEBUG = 1000


def debug_body_printer(max_bytes):
    """
    -> function which can print the response body, for debugging, as a hook
    """

    def debug_body_print(response, *a, **kw):
        data = response.content[:max_bytes]
        urllib3_logger.debug(data)

    return debug_body_print


def debug_requests_on(max_bytes=DEFAULT_MAX_BYTES_DEBUG):
    """Switches on logging of the requests module.

    Response body will be printed as well, up to max_bytes
    """
    global get, post, put, delete

    HTTPConnection.debuglevel = 1
    sesh = Session()
    sesh.hooks["response"] = [debug_body_printer(max_bytes)]
    get = sesh.get
    post = sesh.post
    put = sesh.put
    delete = sesh.delete

    logging.basicConfig(level=logging.DEBUG)
    urllib3_logger.setLevel(logging.DEBUG)
    urllib3_logger.propagate = True
