::

    PEP: XXX
    Title: Isolate subinterpreters
    Author: Victor Stinner <vstinner@python.org>
    Status: Draft
    Type: Standards Track
    Content-Type: text/x-rst
    Created: 23-June-2020
    Python-Version: 3.10

Abstract
========

XXX


Motivation
==========

Python childhood
----------------

When Python is embedded in an application, it is expected to behave as a
dynamic library, not as an application. For example, the ``Py_Main()``
function should not exit the process on error, but return an non-zero
exitcode.

Python was first implemented as an application. The code was not
designed to be embedded into an application. For example, many Python
objects are never destroyed and many memory allocations are never
released at exit: Python expects the operating system to release the
memory anyway when the process completes.

To run multiple Python programs in parallel, Python supports running
multiple interpreters. Usually, the first created interpreter is called
the "main" interpreter since it has special capabilities like signal
handling, and other interpreters are called "subinterpreters".

Again, Python was not designed to run multiple interpreters from the
start. The feature was added after its creation, and so some states
remain shared by all interpretesr. Sometimes, it is done on purpose for
performance, to ease code maintenance. Sometimes, it is more an accident
like a deliberate design choice.

Interpreters must be isolated
-----------------------------

Each interepreter must be isolated from the others. Modifying an
interpreter must not affect the others.

The first rule is to ensure that no Python object is shared: a Python
object created in an interpreter must only be used in this interperter.

Static type limitations
-----------------------

In CPython, it is convenient to declare a types "statically"
(e.g. ``static PyTypeObject MyType = {...};``). The problem is that
static types are shared by all interpreters.

Static types have many limitations compared to heap types:

* Their members are not cleared at exit, they cannot be deallocated.
* Their name cannot be changed.
*

The ``PyHeapTypeObject`` inherits from ``PyTypeObject`` and have more
members:

* ``as_async``
* ``as_buffer``
* ``as_mapping``
* ``as_number``
* ``as_sequence``
* ``ht_cached_keys``
* ``ht_module``
* ``ht_name``
* ``ht_qualname``
* ``ht_slots``

Moreover, when a heap type is allocated, Python allocates more space at
the end for type members defined by ``PyTypeObject.tp_members`` (see
``PyMemberDef`` structure).


Rationale
=========

XXX


Specification
=============

Clear modules at Python exit
----------------------------

XXX

Tracked by `bpo-1635741 <https://bugs.python.org/issue1635741>`_:
Py_Finalize() doesn't clear all Python objects at exit.

Replace static types with heap types
------------------------------------

Replace definiton of static types with heap types created by
``PyType_FromSpec()``.

Tracked by `bpo-40077 <https://bugs.python.org/issue40077>`_: Convert
static types to PyType_FromSpec().


Copyright
=========

This document has been placed in the public domain.
