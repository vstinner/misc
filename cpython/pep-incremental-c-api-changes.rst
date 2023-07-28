++++++++++++++++++++++++++++++
PEP: Incremental C API changes
++++++++++++++++++++++++++++++

Motivation
==========

C API issues
------------

The Python C API has multiple issues: see the
`An Evaluation of Python's C API
<https://github.com/capi-workgroup/problems/blob/main/capi_problems.rst>`_
document of the C API Working group. Most issues are hard to fix and
require incompatible changes. Easy issues which didn't require
incompatible changes were already fixed in the past.

Limits of the D-Day migration approach
--------------------------------------

The Python 2 to Python 3 approach showed limits of a D-Day migration:
require all projects to migrate at once at "the same day". The main
blocker issue was that the proposed tool, 2to3, removed support for the
old API (Python 2), option which was a no-go for many projects
maintainers. The migration only started seriously when a compatibility
layer, the ``six`` module, became popular, so projects can be made
compatible with the new API without losing support for the old API,
which is more an incremental approach than a D-day migration.

Rationale
=========

Chose the changes speed
-----------------------

Adding a new API is always safe, but enforcing the migration takes time:
maintainers of third party extensions are busy with other topics, can be
unavailable for a few months for personal reasons, and some projects are
no longer maintained. With an incremental approach, we can chose when
and how we deprecate old APIs, especially when the old API is removed.

The speed can be adjusted depending on the number of affected projects
and the availability of developers interested to help with such
migration.

The old and the new API can co-exist for a few years. The new API can be
added a first Python version, the old API can be deprecated is a
following version, and the old API removal can happen way later (PEP 387
requires a deprecation for at least two Python versions).

Port C extensions incrementally
-------------------------------

Not only the API is changed incrementally, but migrating C extensions
can also be done incrementally: migrate functions or files one by one.
Since the old API and the API co-exist for a few years, there is no need
to migrate everything "at once.

Code search
-----------

Code search on most popular PyPI projects can be used to identify in
affected projects even before doing an API change. Code search can also
be done in GitHub and services like `grep.app <https://grep.app/>`_ and
`Debian Code Search <https://codesearch.debian.net/>`_.

It helps to estimate the number of affected projects. Projects which are
not published in public, "developed behind closed doors", cannot be
scanned. A solution for that would be to provide a tool which identify C
code affected by planned API changes, but providing such tool is out of
the PEP scope.

Test next Python as early as possible
-------------------------------------

More and more projects are being tested with the "Python nightly build":
the Python main branch. Usually, on a CI job which doesn't block a
change, but is used to get notified of breaking changes.

Moreover, the Fedora project is actively testing alpha versions of
Python by rebuilding all Python packages with the new Python version:
report issues to affected projects, and even sometimes offer a fix.

Contingency Plan: extend deprecation and revert removals
--------------------------------------------------------

If many more affected projects are reported, the migration can be slowed
done by postponing the removal of the old API, or even convert the
deprecation to a soft deprecation (no scheduled removal)

If an API is removed and affected projects are reported after the
removal before a final Python release, the removal can be proposed to
revert to give more time to affected projects to upgrade. The decision
on the revert can depend on the number of affected projects and the
remaining time to upgrade them.


Specification
=============

For each C API issue, propose a new API, upgrade affected projects to
use the new API, and deprecate the old API. Once most affected projects
published a release using the new API, remove the old API.

For minor C API issues, the old API can be only `soft deprecated
<https://peps.python.org/pep-0387/#soft-deprecation>`_ (no scheduled
removal), rather than being "hard" deprecated.

The ideal migration is to only start to deprecate once most affected
projects published a release upgraded to the new API. In practice,
usually the deprecation happens early to give incentives to developers
to migrate. If the old API is not deprecated, only a minority of
developers will upgrade which can block the work on fixing following C
API issues.

The `pythoncapi-compat project
<https://pythoncapi-compat.readthedocs.io/>`_ project can be used to get
the new API on old Python versions, or another compatibility layer.

This document doesn't go into the detail of each issue and proposed
solutions: it should be done on a case by case basis and discussed
separately. This document is only about the general "incremental change"
approach.
