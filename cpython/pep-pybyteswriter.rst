PEP: 757
Title: PyBytesWriter C API
Author: Victor Stinner <vstinner@python.org>
Discussions-To: xxx
Status: Accepted
Type: Standards Track
Created: 06-Feb-2025
Python-Version: 3.14

.. highlight:: c


Abstract
========

Add a new ``PyBytesWriter`` C API to create ``bytes`` object.

It replaces the ``_PyBytes_Resize()`` API which treats an immutable
``bytes`` object as a mutable object.


Rationale
=========

Disallow creation of incomplete/inconsistent objects
----------------------------------------------------

* `Avoid creating incomplete/invalid objects api-evolution#36
  <https://github.com/capi-workgroup/api-evolution/issues/36>`_
* `Disallow mutating immutable objects api-evolution#20
  <https://github.com/capi-workgroup/api-evolution/issues/20>`_
* `Disallow creation of incomplete/inconsistent objects problems#56
  <https://github.com/capi-workgroup/problems/issues/56>`_


Specification
=============

API
---

API::

    typedef struct PyBytesWriter PyBytesWriter;

    PyAPI_FUNC(void*) PyBytesWriter_Create(
        PyBytesWriter **writer,
        Py_ssize_t alloc);
    PyAPI_FUNC(void) PyBytesWriter_Discard(
        PyBytesWriter *writer);
    PyAPI_FUNC(PyObject*) PyBytesWriter_Finish(
        PyBytesWriter *writer,
        void *buf);

    PyAPI_FUNC(void*) PyBytesWriter_Extend(
        PyBytesWriter *writer,
        void *buf,
        Py_ssize_t extend);
    PyAPI_FUNC(void*) PyBytesWriter_WriteBytes(
        PyBytesWriter *writer,
        void *buf,
        const char *bytes,
        Py_ssize_t size);

* Not thread safe.
* Overallocate memory.
* Respect `strict aliasing
  <https://en.wikipedia.org/wiki/Aliasing_(computing)>`_.

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


Rejected Ideas
==============

xxx


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
