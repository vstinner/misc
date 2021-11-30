::

    PEP: xxx
    Title: Disallow using macros as l-value
    Author: Victor Stinner <vstinner@python.org>
    Status: Draft
    Type: Standards Track
    Content-Type: text/x-rst
    Created: 30-Oct-2021
    Python-Version: 3.11


Abstract
========

Incompatible C API change disallowing using macros as l-value to allow
evolving CPython internals and to ease the C API implementation on other
Python implementation.

In practice, projects impacted by these incompatible changes should only
have to make two changes:

* Replace ``Py_TYPE(obj) = new_type;``
  with ``Py_SET_TYPE(obj, new_type);``.
* Replace ``Py_SIZE(obj) = new_size;``
  with ``Py_SET_SIZE(obj, new_size);``.


Rationale
=========

Use a macro as a l-value
------------------------

In the Python C API, some functions are technically implemented as macro
because writing a macro is simpler than writing a regular function. If a
macro exposes directly a struture member, it is technically possible to
use this macro to not only read the structur member but also modify it.
Example with the Python 3.10 ``Py_TYPE()`` macro::

    #define Py_TYPE(ob) (((PyObject *)(ob))->ob_type)

This macro can be used to get an object type::

    type = Py_TYPE(object);

But it can also be used to set an object type::

    Py_TYPE(object) = new_type;

It is also possible to set an object reference count and an object size
using ``Py_REFCNT()`` and ``Py_SIZE()`` macros.

Setting directly an object attribute relies on the current exact CPython
implementation. Implementing this feature in other Python
implementations can make their C API implementation less efficient.

PyPy cpyext module
------------------

For example, the PyPy ``cpyext`` module has to convert PyPy objects to
CPython objects. While PyPy objects are designed to be efficient with
the PyPy JIT compiler, CPython objects are less efficient and increase
the memory usage. In practice, PyPy requires two versions (PyPy and
CPython) of the same objects, and an object is accessed by the C API.

nogil fork
----------

The `Sam Gross' nogil fork of CPython
<https://github.com/colesbury/nogil/>`_ has no ``PyObject.ob_refcnt``
member and so the ``Py_REFCNT(obj) = new_refcnt;`` code is invalid.

It causes compatibility issues to merge this nogil branch into the
upstream CPython main branch.

HPy
---

The `HPy project <https://hpyproject.org/>`_ is a brand new C API for
Python using only handles and function calls: structure members cannot
be accessed directly and pointers cannot be dereferenced. Disallowing
the usage of macros as l-value helps the migratation of existing C
extensions to HPy.


Specification
=============

Disallow using the following macros as l-value:

* PyObject:

  * ``Py_TYPE()``: ``Py_SET_TYPE()`` must be used instead
  * ``Py_SIZE()``: ``Py_SET_SIZE()`` must be used instead

* "GET" functions:

  * ``PyByteArray_GET_SIZE()``
  * ``PyBytes_GET_SIZE()``
  * ``PyCFunction_GET_CLASS()``
  * ``PyCFunction_GET_FLAGS()``
  * ``PyCFunction_GET_FUNCTION()``
  * ``PyCFunction_GET_SELF()``
  * ``PyDict_GET_SIZE()``
  * ``PyFunction_GET_ANNOTATIONS()``
  * ``PyFunction_GET_CLOSURE()``
  * ``PyFunction_GET_CODE()``
  * ``PyFunction_GET_DEFAULTS()``
  * ``PyFunction_GET_GLOBALS()``
  * ``PyFunction_GET_KW_DEFAULTS()``
  * ``PyFunction_GET_MODULE()``
  * ``PyHeapType_GET_MEMBERS()``
  * ``PyInstanceMethod_GET_FUNCTION()``
  * ``PyList_GET_SIZE()``
  * ``PyMemoryView_GET_BASE()``
  * ``PyMemoryView_GET_BUFFER()``
  * ``PyMethod_GET_FUNCTION()``
  * ``PyMethod_GET_SELF()``
  * ``PySet_GET_SIZE()``
  * ``PyTuple_GET_SIZE()``
  * ``PyWeakref_GET_OBJECT()``

* "AS" functions:

  * ``PyByteArray_AS_STRING()``
  * ``PyBytes_AS_STRING()``
  * ``PyFloat_AS_DOUBLE()``

The ``Py_REFCNT()`` macro was already modified in Python 3.10 to
disallow using it as a l-value: ``Py_SET_REFCNT()`` must be used
instead.


Backwards Compatibility
=======================

The proposed C API changes are backward incompatible on purpose.  In
practice, only a minority of third party projects are affected and most
of them have already been prepared for these changes.

Most projects are broken by ``Py_TYPE()`` and ``Py_SIZE()`` changes.
These two macros have been converted to static inline macro in Python
3.10 alpha versions, but the change has been reverted since it broke too
many projects. In the meanwhile, many projects, like Cython, have been
prepared for this change by using ``Py_SET_TYPE()`` and
``Py_SET_SIZE()``. For example, projects using Cython only have to
regenerate their outdated C code to become compatible.

For the "GET" functions like ``PyDict_GET_SIZE()``, no project in the PyPI
top 5000 projects use these functions as l-value.

The ``PyFloat_AS_DOUBLE()`` function is not used as a l-value in the
PyPI top 5000 projects.

The ``PyBytes_AS_STRING()`` and ``PyByteArray_AS_STRING()`` are used as
l-value but only to modify string characters, not to override the
``PyBytesObject.ob_sval`` or ``PyByteArrayObject.ob_start `` member.
For example, Cython uses the following code::

    PyByteArray_AS_STRING(string)[i] = (char) v;

This code remains valid.


References
==========

* `[C API] Disallow using PyFloat_AS_DOUBLE() as l-value
  <https://bugs.python.org/issue45476>`_

Copyright
=========

This document is placed in the public domain or under the
CC0-1.0-Universal license, whichever is more permissive.
