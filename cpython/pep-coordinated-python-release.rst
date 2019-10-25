PEP: xxx
Title: Coordinated Python release
Author: Victor Stinner <vstinner@python.org>
Status: Draft
Type: Standards Track
Content-Type: text/x-rst
Created: 25-Oct-2019
Python-Version: 3.9

Abstract
========

Use 24 projects to detect bugs and to measure the cost of new
incompatible changes before releasing the next Python version.

Rationale
=========

The PEP involves maintainers of a curated list of projects in the Python
release cycle. There are multiple benefit:

* Detect most bugs before a Python release
* Discuss and maybe revert incompatible changes before a Python release
* Increase the number of projects compatible with the next Python
  when the new Python is released

The beta phase is not enough
----------------------------

Currently, Python beta versions are available four months before the
final 3.x.0 release.

Bugs reported during the beta phase can be easily fixed and can block a
release if they are serious enough.

Incompatible changes are discussed during the beta phase: enhance
documentation to update code or consider to revert these changes.

Even if more and more projects are tested on the master branch of Python
in their CI, too many projects of the top 50 projects on PyPI are only
compatible with the new Python a few weeks, or even months, after the
final Python release.

DeprecatedWarning is being ignored
----------------------------------

Python has well defined process to deprecate features. A
DeprecatedWarning must be emited during at least one Python release
before a feature can be removed.

In practice, DeprecatedWarning are ignored for years in major Python
projects. Usually, maintainers explain that there are too many warnings
and so they simply ignore warnings. Moreover, DeprecatedWarning are
silent by default (except in the __main__ module: `PEP 565
<https://www.python.org/dev/peps/pep-0565/>`_).

Even if more and more projects are running their test suite with
warnings treated as errors (``-Werror``), Python core developers still
have no idea how many projects will be broken when a feature is removed.
Usually, it's way greater than one.

Need to coordinate
------------------

When issues and incompatible changes are discovered and discussed after
the final Python release, it becomes way more complicated to fix Python.
Once an API is part of an official final release, usually Python should
provide backward compatibility for the whole 3.x release lifetime. Some
operating systems can be shipped with the buggy final release and can
take several months before being updated.

Too many projects are only updated to the new Python after the final
Python release, which makes this new Python version barely usable to run
large applications.

It is proposed to block a Python release until a curated list of
projects is updated to support the next Python. The best case is when
new project releases are available before the new Python is released,
but it is not strictly required.

Limit the delay
---------------

When a build or test issue with the next Python version is reported to a
project, maintainers have 30 days to answer. With no answer, the project
can be excluded from the list of projects blocking the Python release.

Multiple projects are already tested on the master branch of Python in a
CI. Problems can be detected very early in a Python release which should
provide enough time to handle them. More CI can be added for projects
which are not tested on the next Python yet.

Once problems are known by projects and Python, exceptions can be
discussed between the Python release manager and involved project
maintainers on a case by case basis. Not all issues require to block a
release.


Specification
=============

The Python release manager is responsible to ensure that all projects of
the curated projects list are compatible with the next Python. They can
decide to ignore a project if they decide that the project is going to
be fixed soon enough or if the issue severity is low enough.


Projects blocking a Python release
==================================

24 projects:

* Cython
* Django
* MarkupSafe (needed by Sphinx)
* Sphinx (needed to build Python)
* aiohttp
* certifi (used by urllib3)
* chardet (needed by Sphinx)
* colorama (used by pip)
* cryptography: cffi, pycparser
* docutils (used by Sphinx)
* idna (used by Sphinx and requests)
* jinja2 (needed by Sphinx)
* numpy (needed by scipy and pandas)
* pandas
* pip
* psycopg2 (used by Django)
* pytest (used by tons of Python projects)
* requests
* scipy
* setuptools (used by pip and tons of Python projects)
* six (needed by tons of Python projects)
* sqlalchemy
* urllib3 (used by requests)
* wheel (used by pip)

Design of this list
-------------------

Projects used by to build Python, like Sphinx, must be in the list.

Most popular projects are picked from the most downloaded projects on
PyPI.

Most of project dependencies are included in the list as well, since a
single dependency not compatible with next Python can block a whole
project.

The list should be long enough to have a good idea of the cost of
porting a project to the next Python, but small enough to not block a
Python release for too long.

Obviously, projects which are not part of the list are encouraged to
report issues with the next Python and to have a CI running on the next
Python version.


Incompatible changes
====================

The definition here is large: any Python change which cause an issue
when building or testing a project.

Examples
--------

There are different kinds of incompatible changes:

* Change in the Python build. For example, Python 3.8 removed ``m``
  (which stands for pymalloc) from ``sys.abiflags``.
* Change in the C extensions build. For exmaple, Python 3.8 no longer
  links C extensions to libpython.
* Removed function. For example, collections aliases to ABC classes
  have been removed in Python 3.9.
* Change a function signature:

  * Reject a type which was previously accepted (ex: only accept int,
    reject float)
  * Add a new mandatory parameter.
  * Convert a positional-or-keyword parameter to positional-only

* Behavior change. For example, Python 3.8 now serializes XML attributes
  in their insertion order, rather than sorting them by name.
* New warning. Since more and more projects are testing with warnings
  treated as errors, any new warning can cause a project test to fail.
* Function removed from the C API.
* Structure made opaque in the C API. For example, PyInterpreterState
  became opaque in Python 3.8 which broke projects accessing
  ``interp->modules``: ``PyImport_GetModuleDict()`` must be used
  instead.

Cleaning up Python and DeprecationWarning
-----------------------------------------

One of the `Zen of Python (PEP 20)
<https://www.python.org/dev/peps/pep-0020/>`_ motto is:

    There should be one-- and preferably only one --obvious way to do
    it.

When Python evolves, new ways emerge inevitably. ``DeprecationWarning``
are emitted to suggest to use the new way, but many developers ignore
these warnings, which are silent by default (except in the ``__main__``
module: see the `PEP 565 <https://www.python.org/dev/peps/pep-0565/>`_).
Some developers simply ignore all warnings when there are too many
warnings, and so only bother with exceptions when deprecated code is
removed.

Sometimes, supporting both ways has a minor maintenance cost, but
developers prefer to drop the old way to clean up the code. Such kind of
change is backward incompatible.

Some developers can take the end of the Python 2 support as an
opportunity to push even more incompatible changes than usual.

Adding an opt-in backward compatibility prevents to break
applications and allows developers to continue to do such cleanup.


Distributed CI?
===============

Checking if projects are running well on the master branch of Python may
be automated using a distribured CI. Existing CIs using by each projects
can be used. New CIs might be added.


References
==========

* `PEP 606: Python Compatibility Version
  <https://www.python.org/dev/peps/pep-0606/>`_


Copyright
=========

This document is placed in the public domain or under the
CC0-1.0-Universal license, whichever is more permissive.



..
   Local Variables:
   mode: indented-text
   indent-tabs-mode: nil
   sentence-end-double-space: t
   fill-column: 70
   coding: utf-8
   End:
