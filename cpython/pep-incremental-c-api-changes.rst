++++++++++++++++++++++++++++++
PEP: Incremental C API changes
++++++++++++++++++++++++++++++

Abstract
========

Changing incrementally the Python C API to fix C API issues.

Process to adapt the migration pace depending on the number of affected
projects, available maintainers and remaining time until a new Python
version is released which removes the old API.

Discuss practical solutions to discover affected projects and offer a
compatibility layer to ready for the next Python version without losing
support for old Python versions.


Motivation
==========

C API issues
------------

The Python C API has multiple issues: see the `Evaluation of Python's C
API
<https://github.com/capi-workgroup/problems/blob/main/capi_problems.rst>`_
document of the C API Working group. Most issues are hard to fix and
require incompatible changes. Easy issues are already fixed.

Limits of a flag day migration
------------------------------

The Python 2 to Python 3 migration showed limits of a `flag day
migration <https://en.wikipedia.org/wiki/Flag_day_(computing)>`_:
require all projects to migrate at once at the same day day. The main
blocker issue was that the proposed tool 2to3 removed support for the
old API (Python 2), option which was a no-go for many projects
maintainers. The migration only started seriously when a compatibility
layer, the ``six`` module, became popular, so projects can be made
compatible with the new API without losing support for the old API,
which is more an *incremental approach* than a *flag day migration*.
Migration tools using the compatibility layer were also written.


Rationale
=========

Tune the change pace
--------------------

Adding a new API is always safe, but *enforcing* the migration (with
deprecation) takes time: maintainers of third party extensions are busy
with other topics, can be unavailable for a few months for personal
reasons, and some projects are no longer maintained. With an incremental
migration, we can tune when and how to deprecate old APIs, especially
when the old APIs are removed.

The pace can be adjusted depending on the number of affected projects
and the availability of developers involved in the migration.

The old and the new API can co-exist for a few years. The new API can be
added a first Python version, the old API can be deprecated is a
following version, and the old API removal can happen way later: `PEP
387 <https://peps.python.org/pep-0387/>`_ requires at least a
deprecation for at least two Python versions before removing.

Port C extensions incrementally
-------------------------------

Not only the API is changed incrementally, but migrating C extensions
can also be done incrementally: migrate functions or files one by one.
Since the old API and the API co-exist for a few years, there is no need
to migrate everything "at once.

Code search
-----------

Code search on most popular PyPI projects can be used to identify
affected projects, even before doing an API change. Code search can also
be done in public services like `GitHub Search <https://github.com/>`_,
`Debian Code Search <https://codesearch.debian.net/>`_ and `grep.app
<https://grep.app/>`_.

It helps to estimate the number of affected projects. Projects developed
behind closed door and not published in public cannot be scanned. A tool
identifying C code affected by planned API changes can be provided for
maintainers of these projects, but providing such tool is out of the PEP
scope.

Test next Python as early as possible
-------------------------------------

More and more projects are being tested with the "Python nightly build":
(Python main branch). Usually, on the CI job doesn't block a change, but
is used to get notified of breaking changes as soon as possible.

The Fedora project is actively testing alpha versions of Python by
rebuilding all Python packages with the new Python version: report
issues to affected projects, and even sometimes offer a fix.

Contingency Plan: extend deprecation and revert removals
--------------------------------------------------------

If many affected projects are reported, the migration can be slowed done
by postponing the old API removal, or even convert the deprecation to a
soft deprecation (don't schedule the removal)

If affected projects are reported after an old API removal and before a
final Python release, the removal can be proposed to revert to give more
time to affected projects to upgrade. Usually, it means that the removal
is postponed by one year, in the following Python release. The revert
decision can depend on the number of affected projects and the remaining
time to upgrade them.


Specification
=============

For each C API issue, propose a new API, upgrade affected projects to
use the new API, and deprecate the old API. Once most affected projects
published a release using the new API, remove the old API.

For minor C API issues, the old API can be only `soft deprecated
<https://peps.python.org/pep-0387/#soft-deprecation>`_ (no scheduled
removal), rather than being "hard" deprecated.

The ideal migration is to only start deprecating once most affected
projects published a release upgraded to the new API. In practice,
usually the deprecation happens early to give incentives to migrate. If
the old API is not deprecated, only a minority of developers will
upgrade which can block the work on fixing following more complex C API
issues.

The `pythoncapi-compat project
<https://pythoncapi-compat.readthedocs.io/>`_, or other compatibility
layers, can be used to get the new API on old Python versions.

This document doesn't go into the detail of each issue and proposed
solutions: it should be done on a case by case basis and discussed
separately. This document is only about the general "incremental change"
migration approach.
