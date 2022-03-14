=============
 Fake Sbatch
=============

An stupid app that pretends to be sbatch.

By default, ``fake-sbatch`` will fail 10% of the time (for testing error cases).



Usage
-----

.. code-block:: console

    $ fake-sbatch
    fake-sbatch: Submitted batch job 653898


Settings
--------

If you wish to override the fail percentage (for example, if you wanted it to always or never fail),
you may set the it with: ``FAKE_SBATCH_FAIL_PCT=1.0``. 1.0 means it will always fail. 0.0 means it will
never fail.

You can also control the range of randomly produced slurm job id values by adjusting the ``FAKE_SBATCH_MAX_JOB_ID`` and
``FAKE_SBATCH_MIN_JOB_ID`` settings.


Setting up to use with Jobbergate CLI
-------------------------------------

A simple way to make the ``fake-sbatch`` executable available for jobbergate is to install it via ``pipx``.

Simply, navigate to the root of the ``fake-sbatch`` repository and execute::

   $ pipx install .

Then, in your Jobbergate environment, apply the setting ``SBATCH_PATH=fake-sbatch``
