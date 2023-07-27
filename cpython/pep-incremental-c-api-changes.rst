++++++++++++++++++++++++++++++++++++++++++++
PEP: Incremental changes in the Python C API
++++++++++++++++++++++++++++++++++++++++++++

Motivation
==========

C API issues
------------

The Python C API has multiple issues: see the
`An Evaluation of Python's C API
<https://github.com/capi-workgroup/problems/blob/main/capi_problems.rst>`_
document of the C API Working group. Each issue is hard to fix and
likely require incompatible changes. Easy issues which didn't require
incompatible changes were already fixed in the past.

Limits of the D-Day migration approach
--------------------------------------

The Python 2 to Python 3 approach showed limits of a D-Day migration:
require all projects to migrate at once at "the same day". The main
blocker issue was that the proposed tool, 2to3, removed support for the
old API (Python 2), option which was a no-go for many project
maintainers. The migration only really started when a compatibility
layer, the ``six`` module, became popular, so projects can come
compatible with the new API without losing support for the old API.

Rationale
=========

XXX

Specification
=============

Incremental change
------------------

For each C API issue, propose a new API which address the process, soft
deprecate or deprecate the old API, upgrade projects to use the new API
by using the `pythoncapi-compat project
<https://pythoncapi-compat.readthedocs.io/>`_ project to get the new API
on old Python version. Once the number of projects still using the old
API becomes resonable, consider removing the old API.

This document doesn't go into the detail of each issue and proposed
solution: it should be done on a case by case basis and discussed
separately. This document is more about the general "incremental change"
approach.

Process
-------

XXX https://peps.python.org/pep-0620/#process-to-reduce-the-number-of-broken-c-extensions

pythoncapi-project
------------------

`The project was created
<https://vstinner.github.io/pythoncapi_compat.html>`_ when What's New
documents got more and more recipes to provide new functions on old
Python, like::

    #if PY_VERSION_HEX < 0x030900A4
    #  define Py_SET_TYPE(obj, type) ((Py_TYPE(obj) = (type)), (void)0)
    #endif

    #if PY_VERSION_HEX < 0x030900A4
    #  define Py_SET_REFCNT(obj, refcnt) ((Py_REFCNT(obj) = (refcnt)), (void)0)
    #endif

    #if PY_VERSION_HEX < 0x030900A4
    #  define Py_SET_SIZE(obj, size) ((Py_SIZE(obj) = (size)), (void)0)
    #endif

pythoncapi-compat is a header file implementing new API functions using
old functions. It has a documentation and tests. It supports Python 2.7
to 3.13, PyPy2 and PyPy3. C++ compatibility is also tested on Python 3.6
and newer. Python 2.7-3.5 are no longer officially supported, but should
still work (best effort maintenance).

It also provide ``upgrade_pythoncapi.py`` which adds support for new
Python versions by using new API, to avoid deprecated and removed
functions. The tool adds ``#include "pythoncapi_compat.h"`` to keep
support with old Python versions (get new functions on old Python
versions).

pythoncapi-compat got adopted by projects with a large C code base like
PyTorch and Mercurial. Its Zero Clause BSD license was chosen to avoid
licensing issue since ``pythoncapi_compat.h`` header file should be
copied to the project directly.

Cython and numpy have a similar approach to backward compatibility using
their own compatibility layer.


Examples of Python 3.7-3.13 changes done incrementally
======================================================

Move private and internal API to the internal C API
---------------------------------------------------

In Python 3.7, a new ``Include/internal/`` directory was created for the
"internal C API". Between Python 3.7 and 3.13, more and more privates
are being moved there: each release moves a bunch of private functions
there.

The internal C API is exposed to third party projects, but it requires
to define a specific ``Py_BUILD_CORE`` macro and the header files
are less easy to use.

Moreover, more and more internal C API are no longer exported and so
cannot be called by third party projects. Debuggers and profilers can
use internal C structures to inspect Python internal state without
modifying this state nor having to call functions.

Make PyGC_Head structure opaque
-------------------------------

In Python 3.9 (2020), see `issue GH-84422
<https://github.com/python/cpython/issues/84422>`_ and `commit
<https://github.com/python/cpython/commit/0135598d729d01f35ce08d47160adaa095a6149f>`__.

No project was affected by this change.

`Issue GH-83780 <https://github.com/python/cpython/issues/83780>`_:
ABI breakage between Python 3.7.4 and 3.7.5: change in PyGC_Head structure.

Deprecate and remove functions
------------------------------

See `C API changes between Python 3.5 to 3.10
<https://vstinner.github.io/c-api-python3_10-changes.html>`_ (2021) by
Victor Stinner.

Prepare making PyObject structure opaque
----------------------------------------

See `issue GH-83754 <https://github.com/python/cpython/issues/83754>`_.
Avoid accessing directly PyObject members in the public C API.

* Add Py_IS_TYPE() function

Disallow using macros as l-value
--------------------------------

Py_REFCNT(), Py_TYPE() and Py_SIZE() macros can no longer be used as
l-value to set an object reference count, type or size:

* ``Py_SET_REFCNT()``, ``Py_SET_TYPE()`` and ``Py_SET_SIZE()`` were
  added to Python 3.9.
* ``Py_REFCNT()`` macro was `converted to a static inline function
  <https://github.com/python/cpython/commit/fe2978b3b940fe2478335e3a2ca5ad22338cdf9c>`_
  in Python 3.10: cannot be used as l-value to set the reference count
  anymore.
* ``Py_TYPE()`` and ``Py_SIZE()`` macros was converted to static inline
  functions in a similar way in Python 3.11. This change was first done
  in May 2020 but reverted in November. Most affected projects got
  updated before the `change was done again
  <https://github.com/python/cpython/commit/cb15afcccffc6c42cbfb7456ce8db89cd2f77512>`_
  in September 2021.  See `PEP 674: Py_TYPE() and Py_SIZE() macros
  <https://peps.python.org/pep-0674/#py-type-and-py-size-macros>`_.

Py_TYPE() got a steering council exception, whereas Py_SIZE() didn't and
PEP 674 got rejected. Sadly, nobody reminded to revert Py_SIZE() change
(done before PEP 674 was written and then rejected) and so it landed in
Python 3.11.

Most affected projects use the pythoncapi-project to get new "SET"
functions on Python 3.8 and older.

Prepare making PyTypeObject structure opaque
--------------------------------------------

Python 3.9 (2020), avoid accessing PyTypeObject members in the public
C API:

* `issue GH-84351 <https://github.com/python/cpython/issues/84351>`_

Prepare making PyTheaadState structure opaque
---------------------------------------------

See `issue GH-84128 <https://github.com/python/cpython/issues/84128>`_

Python 3.9: add getter functions:

* PyThreadState_GetFrame()
* PyThreadState_GetID()
* PyThreadState_GetInterpreter()

Python 3.11:

* PyThreadState_EnterTracing()
* PyThreadState_LeaveTracing()

Convert macros to functions
---------------------------

Convert macros to static inline functions.

Implemented in Python 3.11 and 3.12, see
`PEP 670 – Convert macros to functions in the Python C API
<https://peps.python.org/pep-0670/>`_
and
`Convert macros to functions <https://vstinner.github.io/c-api-convert-macros-functions.html>`_.

Work started in Python 3.8:

* Py_INCREF(), Py_XINCREF()
* Py_DECREF(), Py_XDECREF()
* PyObject_INIT(), PyObject_INIT_VAR()
* _PyObject_GC_TRACK(), _PyObject_GC_UNTRACK(), _Py_Dealloc()

Python 3.9:

* PyIndex_Check()
* PyObject_CheckBuffer()
* PyObject_GET_WEAKREFS_LISTPTR()
* PyObject_IS_GC()
* PyObject_NEW(): alias to PyObject_New()
* PyObject_NEW_VAR(): alias to PyObjectVar_New()

Move PyInterpreterState to the internal C API
---------------------------------------------

Remove PyInterpreterState members from the public C API in Python 3.8.
See `issue bpo-35886 <https://bugs.python.org/issue35886>`_.

Borrowed references
-------------------

* Python 3.10:

  * Add ``Py_NewRef()`` and ``Py_XNewRef()``
  * Add `borrowed reference
    <https://docs.python.org/dev/glossary.html#term-borrowed-reference>`_
    and `strong reference
    <https://docs.python.org/dev/glossary.html#term-strong-reference>`_
    to the documentation glossary.
  * Add ``PyModule_AddObjectRef()``

* Python 3.13

  * Add ``PyDict_GetItemRef()``, ``PyWeakref_GetRef()``,
    ``PyImport_AddModuleRef()``.

In 2021, adding PyTuple_GetItemRef() got rejected:
`issue GH-86460 <https://github.com/python/cpython/issues/86460>`_

Move PyFrameObject to the internal C API
-----------------------------------------

Remove PyFrameObject members from the public C API in Python 3.11
alpha6:
see `issue GH-90992 <https://github.com/python/cpython/issues/90992>`_
and `commit <https://github.com/python/cpython/commit/18b5dd68c6b616257ae243c0b6bb965ffc885a23>`__

The change affected Cython, greenlet and gevent which were quickly
upgraded.

Helper functions were added for this change in Python 3.11:

* PyFrame_GetBuiltins()
* PyFrame_GetGenerator()
* PyFrame_GetGlobals()
* PyFrame_GetLasti()
* PyFrame_GetLocals()

The change was prepared in Python 3.9 by adding two getter functions:

* PyFrame_GetBack()
* PyFrame_GetCode()
* Moreover, PyFrame_GetLineNumber() was moved to the internal C API

In Python 3.12, new helper functions were added:

* PyFrame_GetVar()
* PyFrame_GetVarString()
