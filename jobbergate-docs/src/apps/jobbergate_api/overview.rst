=========================
 Jobbergate API Overview
=========================

The `Jobbergate API`_ is a RESTful API that serves as the back-end for the system. It serves data for the Jobbergate CLI
and any other interfaces and automations that need to connect with Jobbergate resources.

There jobbergate-api offers interactive documentation via `swagger`_.

The API's endpoints are secured and require valid JWTs issued by the OIDC provider the
API is configured with.

.. TODO::

   reference the documentation for setting up OIDC


.. _`Jobbergate API`: https://github.com/omnivector-solutions/jobbergate/jobbergate-api
.. _`swagger`: https://armada-k8s.staging.omnivector.solutions/jobbergate/docs>
