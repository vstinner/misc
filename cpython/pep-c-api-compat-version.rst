+++++++++++++++++++++++++++++++++++++++++
Add Py_COMPAT_API_VERSION to Python C API
+++++++++++++++++++++++++++++++++++++++++

Target version: Python 3.13

Abstract
========

Add ``Py_COMPAT_API_VERSION`` and ``Py_COMPAT_API_VERSION_MAX`` macros
to decide **when** a C extension is impacted by incompatible changes.


Rationale
=========

The Python C API evolves at each Python version and gets a bunch of
changes. Some of them are backward incompatible: C extensions must be
updated to work on the new Python. Some incompatible changes are driven
by new features: they cannot be avoided, unless we decide to not add
these features. Some incompatible changes are driven by other reasons:

* Remove deprecated API (see PEP 387).
* Ease the implementation of another change.
* Change or remove error-prone API.
* Other reasons.

Currently, there is no middle ground between "not change the C API" and
"incompatible C API impacting everybody".

The limited C API is versionned: the ``Py_LIMITED_API`` macro can be set
to a Python version to select which API is available. On the Python
side, it allows introducing incompatible changes at a specific
``Py_LIMITED_API`` version. For example, if ``Py_LIMITED_API`` is set to
Python 3.11 or newer, the ``<stdio.h>`` is no longer included by
``Python.h``.

The difference here is that upgrading Python does not change if
``<stdio.h>`` is included or not, but updating ``Py_LIMITED_API`` does,
and updating ``Py_LIMITED_API`` is an action made by C extension
maintainer. It gives more freedom to decide **when** the maintainer is
ready to deal with the latest batch of incompatible changes.


Specification
=============

Add a new ``Py_COMPAT_API_VERSION`` macro which can be set by users of the C
API to opt-in to be compatible with future Python versions. Example for
Python 3.13 scheduling the removal of an API in Python 3.15::

    #if Py_COMPAT_API_VERSION < 0x030f0000
    Py_DEPRECATED(3.13) PyAPI_FUNC(PyObject *) PyImport_ImportModuleNoBlock(
        const char *name            /* UTF-8 encoded string */
        );
    #endif

If the ``Py_COMPAT_API_VERSION`` macro is not set, it is to
``PY_VERSION_HEX`` by default.

Building a C extension with ``Py_COMPAT_API_VERSION`` set to
``Py_COMPAT_API_VERSION_MAX`` checks for future incompatible changes: it
helps to make a C extension compatible with future Python versions. It
can also be set to a specific version. For example, ``#define
Py_COMPAT_API_VERSION 0x030f0000`` checks for changes up to Python 3.15
(included).

The macro can be set in a single C file or for a whole project in
compiler flags. The macro does not affected other projects or Python
itself, its scope is "local".

Goals:

* Reduce the number of incompatible C API changes affecting C extensions
  on a Python upgrade.
* For C extensions tests, ``Py_COMPAT_API_VERSION`` can be set to
  ``Py_COMPAT_API_VERSION_MAX`` to detect future incompatibilities. For C
  extensions releases, it can be set a fixed Python version.
* For core developers, make sure that the C API can still evolve
  without being afraid of broking an unknown number of C extensions.

Non-goals:

* Freeze the API forever: this is not the stable ABI. For example,
  deprecated functions will continue to be removed on a regular basis.
  Not updating ``Py_COMPAT_API_VERSION`` does not prevent C extensions
  maintainers to update their code: incompatible changes will still
  happen soon or later.
* Provide a stable ABI: the macro only impacts the API.
* Silver bullet solving all C API issues.


Examples which can use Py_COMPAT_API_VERSION
============================================

* Remove deprecated functions. Example: ``PyImport_ImportModuleNoBlock``
  deprecated in Python 3.13.
* Remove deprecated members of a structure, such as
  ``PyBytesObject.ob_shash``.

Prior Art
=========

* ``Py_LIMITED_API`` macro of `PEP 384 – Defining a Stable ABI
  <https://peps.python.org/pep-0384/>`_.
* Rejected `PEP 606 – Python Compatibility Version
  <https://peps.python.org/pep-0606/>`_ which has a global scope.
