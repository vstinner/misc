::

    PEP: xxx
    Title: PyBytesWriter C API
    Author: Victor Stinner <vstinner@python.org>
    Discussions-To: xxx
    Status: Draft
    Type: Standards Track
    Created: 06-Feb-2025
    Python-Version: 3.14


.. highlight:: c


Abstract
========

Add a new ``PyBytesWriter`` C API to create ``bytes`` object.

It replaces the ``PyBytes_FromStringAndSize(NULL, size)`` and
``_PyBytes_Resize()`` APIs which treat an immutable ``bytes`` object as
a mutable object.


Rationale
=========

Disallow creation of incomplete/inconsistent objects
----------------------------------------------------

Creating a Python :class:`bytes` object using
``PyBytes_FromStringAndSize(NULL, size)`` and ``_PyBytes_Resize()``
treats an immutable :class:`bytes` object as mutable. It goes against
the principle that :class:`bytes` objects are immutable. It also creates
an incomplete or "invalid" object since bytes are not initialized. In
Python, a :class:`bytes` object should always have its bytes fully
initialized.

* `Avoid creating incomplete/invalid objects api-evolution#36
  <https://github.com/capi-workgroup/api-evolution/issues/36>`_
* `Disallow mutating immutable objects api-evolution#20
  <https://github.com/capi-workgroup/api-evolution/issues/20>`_
* `Disallow creation of incomplete/inconsistent objects problems#56
  <https://github.com/capi-workgroup/problems/issues/56>`_

Overallocation
--------------

When the output size is unknown, there are two strategy:

* Overallocate by the worst case, and then shrink at the end.
* Extend the buffer when a larger write is needed.

Both strategies are inefficient. Overallocating by the worst case
consumes too much memory. Extending the buffer multiple times is
inefficient.

A better strategy is to overallocate the buffer when extending the
buffer to reduce the number of expensive ``realloc()`` operations which
can imply a memory copy.


Specification
=============

API
---

.. c:type:: PyBytesWriter

   A Python :class:`bytes` writer instance created by
   :c:func:`PyBytesWriter_Create`.

   The instance must be destroyed by :c:func:`PyBytesWriter_Finish` or
   :c:func:`PyBytesWriter_Discard`.

.. c:function:: void* PyBytesWriter_Create(PyBytesWriter **writer, Py_ssize_t alloc)

   Create a :c:type:`PyBytesWriter` to write *alloc* bytes.

   If *alloc* is greater than zero, allocate *alloc* bytes for the
   returned buffer.

   On success, return non-``NULL`` buffer where bytes can be written.
   On error, set an exception and return ``NULL``.

   *alloc* must be positive or zero.

.. c:function:: void PyBytesWriter_Discard(PyBytesWriter *writer)

   Discard a :c:type:`PyBytesWriter` created by :c:func:`PyBytesWriter_Create`.

   The writer instance is invalid after the call.

.. c:function:: PyObject* PyBytesWriter_Finish(PyBytesWriter *writer, void *buf)

   Finish a :c:type:`PyBytesWriter` created by :c:func:`PyBytesWriter_Create`.

   On success, return a Python :class:`bytes` object.
   On error, set an exception and return ``NULL``.

   The writer instance is invalid after the call.

.. c:function:: void* PyBytesWriter_Extend(PyBytesWriter *writer, void *buf, Py_ssize_t extend)

   Add *extend* bytes to the buffer: allocate *extend* bytes in addition
   to bytes already allocated by previous :c:func:`PyBytesWriter_Create`
   and :c:func:`PyBytesWriter_Extend` calls.

   On success, return non-``NULL`` buffer where bytes can be written.
   On error, set an exception and return ``NULL``.

   *extend* must be positive or zero.

.. c:function:: void* PyBytesWriter_WriteBytes(PyBytesWriter *writer, void *buf, const char *bytes, Py_ssize_t size)

   Extend the buffer by *size* bytes and write *bytes* into the writer.

   If *size* is equal to ``-1``, call ``strlen(bytes)`` to get the
   string length.

   On success, return non-``NULL`` buffer.
   On error, set an exception and return ``NULL``.

.. c:function:: void* PyBytesWriter_Format(PyBytesWriter *writer, void *buf, const char *format, ...)

   Similar to ``PyBytes_FromFormat()``, but write the output directly
   into the writer.

   On success, return non-``NULL`` buffer.
   On error, set an exception and return ``NULL``.

.. c:function:: Py_ssize_t PyBytesWriter_GetAllocated(PyBytesWriter *writer)

   Get the number of allocated bytes.


Overallocation
--------------

:c:func:`PyBytesWriter_Extend` overallocates the buffer to reduce the
number of ``realloc()`` calls and to reduce memory copies.


Strict aliasing
---------------

:c:func:`PyBytesWriter_Create`, :c:func:`PyBytesWriter_Extend` and
:c:func:`PyBytesWriter_WriteBytes` functions return the new buffer as
the result, rather than taking a ``void**`` or ``char**`` argument
modified in-place to avoid issues with `strict aliasing
<https://en.wikipedia.org/wiki/Aliasing_(computing)>`_.

Thread safety
-------------

The API is not thread safe: a writer should only be used by a single
thread at the same time.

Examples
--------

Example creating the string "abc", with a fixed size of 3 bytes::

    PyObject* create_abc(void)
    {
        PyBytesWriter *writer;
        char *str = PyBytesWriter_Create(&writer, 3);
        if (writer == NULL) return NULL;

        memcpy(str, "abc", 3);
        str += 3;

        return PyBytesWriter_Finish(writer, str);
    }

Example formatting an integer in decimal, the size is not known in
advance::

    PyObject* format_int(int value)
    {
        PyBytesWriter *writer;
        char *str = PyBytesWriter_Create(&writer, 20);
        if (writer == NULL) return NULL;

        str += PyOS_snprintf(str, 20, "%i", value);

        return PyBytesWriter_Finish(writer, str);
    }


Implementation
==============

xxx


Backwards Compatibility
=======================

There is no impact on the backward compatibility, only new APIs are
added.


Projects using _PyBytes_Resize()
================================

A code search on PyPI top 8,000 projects finds 41 projects using
``_PyBytes_Resize``:

* Nuitka (2.6)
* PyBluez (0.23)
* PyICU (2.14)
* PyICU-binary (2.7.4)
* SimpleParse (2.2.4)
* apsw (3.48.0.0)
* asyncio (3.4.3)
* billiard (4.2.1)
* bitarray (3.0.0)
* blosc (1.11.2)
* casadi (3.6.7)
* catboost (1.2.7)
* cython (3.0.11)
* ddtrace (2.20.0)
* deflate (0.7.0)
* isal (1.7.1)
* m2crypto (0.43.0)
* msgspec (0.19.0)
* multiprocess (0.70.17)
* mysql-connector (2.2.9)
* mysql-connector-python-rf (2.2.2)
* mysqlclient (2.2.7)
* orjson (3.10.15)
* ormsgpack (1.7.0)
* pickle5 (0.0.12)
* pillow (11.1.0)
* psycopg2 (2.9.10)
* psycopg2-binary (2.9.10)
* pyarrow (19.0.0)
* pybase64 (1.4.0)
* pygobject (3.50.0)
* pygresql (6.1.0)
* pyobjc_core (11.0)
* pysam (0.22.1)
* pyzstd (0.16.2)
* rcssmin (1.2.0)
* rjsmin (1.2.3)
* zipfile-deflate64 (0.2.0)
* zlib_ng (0.5.1)
* zodbpickle (4.1.1)
* zstandard (0.23.0)


Discussions
===========

* Second public API attempt:

  * `Issue gh-129813 <https://github.com/python/cpython/issues/129813>`_
    and
    `pull request gh-129814
    <https://github.com/python/cpython/pull/129814>`_
    (February 2025)

* First public API attempt:

  * C API Working Group decision:
    `Add PyBytes_Writer() API
    <https://github.com/capi-workgroup/decisions/issues/39>`_
    (August 2024)
  * `Pull request gh-121726
    <https://github.com/python/cpython/pull/121726>`_:
    first public API attempt (July 2024)

* `Fast _PyAccu, _PyUnicodeWriter and_PyBytesWriter APIs to produce
  strings in CPython <https://vstinner.github.io/pybyteswriter.html>`_
  (March 2016)


Copyright
=========

This document is placed in the public domain or under the
CC0-1.0-Universal license, whichever is more permissive.
