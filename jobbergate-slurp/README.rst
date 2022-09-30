==================
 Jobbergate Slurp
==================

Jobbergate Slurp is a utility tool that provides support for migrating from legacy
versions of Jobbergate to the latest version.

It pulls existing Jobbergate resources out of a legacy database and file store and moves
the entries into a modern jobberate database and file store. Along the way, it remaps
some columns and makes other adjustments as needed to preserve compatibility.

It's not recommended that anyone but SMEs for Jobbergate use Slurp, as it is a very
specifically tailored app for legacy deployments (that all use very old versions).


License
-------
* `MIT <LICENSE>`_


Copyright
---------
* Copyright (c) 2021 OmniVector Solutions <info@omnivector.solutions>
