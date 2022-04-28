=========================
 Local Development Setup
=========================

There are several options available for running parts of Jobbergate locally. This
document will walk through the most important ones.


Local jobbergate-cli setup
--------------------------

The ``jobbergate-cli`` is the easiest component to set up locally. It is designed so
that it may be deployed anywhere and only needs to be connected to an API.


Create a new application in Auth0
.................................

Before you begin, you will need to have an Auth0 application setup for your instance of
the ``jobbergate-cli``. Request one of the senior Armada engineers to set one up for
you. When the setup is done, you will be provided two values that you will need for
configuration:

* ``client_id``
* ``client_secret``

Save these for later.


Clone the git repo
..................

Start by cloning the `jobbergate <https://github.com/omnivector-solutions/jobbergate>`_
repository and changing to the ``jobbergate-cli`` directory:

.. code-block:: bash

   $ git clone git@github.com:omnivector-solutions/jobbergate.git
   $ cd jobbergate/jobbergate-cli


Install the python package
..........................

Next, you will need to install the package. The ``jobbergate-cli`` package uses
`Poetry <https://pytyhon-poetry.org/>`_ for dependency and virtualenv management. Run
this command to install the package:

.. code-block:: bash

   $ poetry install


Configure things
................

Now, you will need to set up a local ``.env`` file containing some required settings.
You will need to use the ``client_id`` and ``client_secret`` you got from the Auth0 setup
step.

Below is the minimum set of configuration values you will need to set::

   JOBBERGATE_API_ENDPOINT=https://armada-k8s.staging.omnivector.solutions/jobbergate
   AUTH0_DOMAIN=omnivector.us.auth0.com
   AUTH0_LOGIN_DOMAIN=login.omnivector.solutions
   AUTH0_AUDIENCE=https://armada.omnivector.solutions
   AUTH0_CLIENT_ID=<client_id>
   AUTH0_CLIENT_SECRET=<client_secret>


Check it out
............

Now, to make sure that things are configured correctly, try logging in and fetching a
list of applications. For all the jobber gate commands, you will either need to be
executing them inside a poetry shell or prefixing them with a ``poetry run`` command.
The easiest way is to run in a poetry shell:

.. code-block:: bash

   $ poetry shell

Now, you are operating inside of the virtualenv that Poetry uses internally. All
``jobbergate`` commands should be available to you. You can see the available commands
and a basic usage guide for Jobbergate with this command:

.. code-block:: bash

   $ jobbergate --help

To interact with any of the Jobbergate entities, you will first need to login. To do
this, run the following command and follow the link it shows:

.. code-block:: bash

   $ jobbergate login

You may use your Google Workspace user to sign in. When you have successfully completed
the login process, the CLI will print out a message that looks like this::

   ╭──────────────────────────────── Logged in! ───────────────────────────────────────╮
   │                                                                                   │
   │   User was logged in with email '<your-name>@omnivector.solutions'                │
   │                                                                                   │
   ╰───────────────────────────────────────────────────────────────────────────────────╯

Now, lets see a list of applications to make sure we are properly connected to the API:

.. code-block:: bash

   $ jobbergate applications list --all

You should see a lot of lines in a table that looks something like::

   ┏━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
   ┃ id  ┃ application_name       ┃ application_identifier ┃ application_description            ┃ application_owner_email            ┃ application_uploaded ┃
   ┡━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
   │ 6   │ test_chain             │ aaaaaaaa               │ bbbbbbb                            │ bdx@bdx.com                        │ False                │
   │ 68  │ 00_smallcase_TEST_00_1 │ None                   │ smallcaseratssssss                 │ james.beedy@scania.com             │ True                 │
   │ 67  │ 00_smallcase_TEST      │ None                   │ smallcaseratssssss                 │ james.beedy@scania.com             │ True                 │
   │ 75  │ BDXTEST                │ None                   │ RATS                               │ james.beedy@scania.com             │ True                 │
   │ 78  │ converge-test          │ converge-app           │                                    │ abdallah.el-hajjam@scania.com      │ True                 │
   │ 84  │ 00_smallcase           │ None                   │ Small application for testing      │ james.beedy@scania.com             │ True                 │
   │     │                        │                        │ jobbergate.                        │                                    │                      │
   ...
   │ 91  │ tucker-test            │ tucker-test            │                                    │ tucker@omnivector.solutions        │ True                 │
   └─────┴────────────────────────┴────────────────────────┴────────────────────────────────────┴────────────────────────────────────┴──────────────────────┘

If you see this kind of output, congratulations! You now have a local instance of
``jobbergate-cli`` working and ready for develoment.

Make sure to deactivate the Poetry virtualenv before you move on by typing "exit" or
hitting ``<ctl-d>``.


Local jobbergate-api setup
--------------------------

The easiest way to set up ``jobbergate-api`` for local development is using
``docker-compose``. There is a ``docker-compose.yml`` in the root directory of the main
``jobbergate`` repository that can be used to spin up the following services:

* The ``jobbergate-api``
* A local ``postgres`` instance for the ``jobbergate-api`` to consume
* A test ``postgres`` instance to use for the unit tests
* A ``minio`` instance for mimicing file storage on ``S3``


Create some basic config
........................

First, ``docker-compose`` will need a ``.env`` file that contains some basic settings.
Create the ``.env`` file in the root ``jobbergate`` directory with the following
contents::

   AUTH0_DOMAIN=omnivector.us.auth0.com
   AUTH0_AUDIENCE=https://armada.omnivector.solutions


Stand it up with ``docker-compose``
...................................

If you haven't already, `Clone the git repo`_.  From the root directory of the
``jobbergate`` directory, execute ``docker-compose``:

.. code-block:: bash

   $ docker-compose up --build

Wait until the compose finishes.



Try out the API with Swagger
............................

Next we want to try out the API in a browser using Swagger. To do this, you will need
a functioning auth token with Jobbergate permissions. The easiest way to do this is to
use the ``jobbergate-cli``.

Change to the ``jobbergate-cli`` directory and activate the Poetry shell again. Then
show the cached auth token (you will need to login if you haven't yet):

.. code-block:: bash

   $ cd jobbergate-cli
   $ poetry shell
   $ jobbergate show-token --prefix --plain

The token will automatically be copied to your clipboard for you. You can also just
copy it from the output if you like. You may now exit the Poetry shell and go back to
the root ``jobbergate`` directory.

Now, open a browser to the ``jobbergate-api`` swagger page at
`localhost:8000/jobbergate/docs <http://localhost:8000/jobbergate/docs>`_.

You should see a listing of all the endpoints that are available to you. However, you
will need to add your auth token to swagger to pull any data from them. To do this,
click on the small lock icon in the upper right and paste the token you copied earlier.
Once you have confirmed this, the endpoints should all accept your requests.

None of them will be very interesting at this point, though, because the database you
are using in docker is empty.


Configure `jobbergate-cli` to use the local API
...............................................

At this point, you may configure your local ``jobbergate-cli`` to connect to your local
``jobbergate-api``. To do this, navigate to the ``jobbergate-cli`` directory and edit
the ``.env`` file you created ealier to use the local API::

   JOBBERGATE_API_ENDPOINT=https://localhost:8000/jobbergate


Now, you can use ``jobbergate-cli`` to manipulate your local instance of jobbergate.


Connect local jobbergate-api with staging database
--------------------------------------------------

If you want to connect your local API with a database that is already populated with
data, you may connect your local ``jobbergate-api`` instance in ``docker-compose`` to
the staging jobbergate database.

To do this, you must:

* Have already configured aws-cli with your AWS credentials
* Have already configured kubectl to use the ``armada-k8s-cluster-staging`` cluster

If you have Jobbergate services running in ``docker-compose``, you will first need to
shut them down with this command:

.. code-block:: bash

   $ docker-compose down


Next, you will use ``kubectl`` to port-forward a local port to the Jobbergate database
hosted on the EKS Armada staging cluster. Use this command:

.. code-block:: bash

   $ kubectl port-forward service/jobbergate-postgres-cluster 8432:5432

Now, your local port 8432 will connect to the Postgres database in the Armada staging
cloud.

Next, we will need to set up a local configuration to override the defaults in the
``docker-compose.yml`` file. Change to the root ``jobbergate`` directory, and edit the
``.env`` file  you created earlier. You will need to add the following lines::

   DATABASE_HOST=localhost
   DATABASE_USER=omnivector
   DATABASE_PSWD=<retrieve-from-1password>
   DATABASE_NAME=jobbergate
   DATABASE_PORT=8432

The password you will have to get from `1password <https://omnivector.1password.com>`_.

Now, start the Jobbergate services up againt with ``docker-compose``:

.. code-block:: bash

   $ docker-compose up

You can now check to see if your local ``jobbergate-api`` is connected to the staging
database by opening its swagger in a browser and executing one of the ``list``
endpoints. You should get a 200 response with some data.
