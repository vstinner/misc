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

PEP 489: Multi-phase extension module initialization
----------------------------------------------------

XXX

Combined with `PEP 573 -- Module State Access from C Extension Methods
<https://www.python.org/dev/peps/pep-0573/>`_ (Python 3.9).

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

What if subinterpreters are not faster?
---------------------------------------

The work required to better isolate subinterpreters will benefit to
CPython design even if subinterpreters are not used. Most of the work
benefit to the "embed Python in an application" use case:

* Creation and destruction of Python object is better controlled.
* In the long term, all Python objects and all memory will be released
  by Py_Finalize().
* Python will stop to rely on global variables and have a better defined
  "state".

Spawning child processes is not always an option
------------------------------------------------

When Python is embedded in an application, it is not convenient to spawn
child processes to workaround the GIL performance limitation.

Windows doesn't support forking a process and spawning a child process
is more expensive than spawning a thread.

On macOS, running arbitrary code fork() is no longer safe: only
fork()+exec() or posix_spawn() are safe.


Specification
=============

Pass tstate explicitly to internal C functions
----------------------------------------------

XXX

* https://bugs.python.org/issue36710
* https://bugs.python.org/issue38644

Misc
----

* Fix the signal handler: always use the main interpreter.
* Pending calls: bpo-39984

Daemon threads
--------------

XXX

Move shared states per-interpreter
----------------------------------

The ``PyInterpreterState`` structure was made opaque in Python 3.8.

* GC state (``PyInterpreterState.gc``): completed in https://bugs.python.org/issue36854#msg357150
* parser state (``PyInterpreterState.parser``): completed in https://bugs.python.org/issue36876
* warnings state (``PyInterpreterState.warnings``):  completed in https://bugs.python.org/issue36737

Free lists:

* XXX
* XXX
* XXX

Misc:

* small int singletons: https://github.com/python/cpython/commit/ef5aa9af7c7e493402ac62009e4400aed7c3d54e
* empty tuple singleton
* None, True, False, Ellipsis singletons: https://bugs.python.org/issue39511


Per-interpreter GIL
-------------------

XXX

Tracked by `bpo-40512 <https://bugs.python.org/issue40512>`_:
Meta issue: per-interpreter GIL.

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


Subinterpreter Limitations
==========================

Crash
-----

If an extension module does crash, the whole process is killed: all
interpreters are killed immediately. Multiprocessing limits code
impacted by crashes.

Multithreaded applications have the same limitation: a crash in a thread
kills immediately all threads.

Need to update extension modules
--------------------------------

Extension modules should be updated to use PEP 489 "Multiphase
Initialization Module" and replace static types with heap allocated
types (use ``PyType_FromSpec()``). Also, global variables have be moved
to a "module state" and module functions have to be modified to retrieve
this module state.

PEP 554
-------

In its current shape, the PEP 554 is quite limited and doesn't offer an
helper to easily share "objects" between interpreters. A Python object
must only be used in the interpreter where it was created.

It may be possible to share data and create thin proxies as Python
objects to access these data from multiple interpreters. So far, no
standard synchronization primitive is available.

Subinterpreters may be as fast or slower than multiprocessing
-------------------------------------------------------------

It is possible to share data between processes as it is possible
beetween threads. So far, nothing proves that subinterpreters will be
faster than multiprocessing.

In Python 3.8, multiprocessing supports shared memory and pickle
protocol 5 supports out-of-band buffers.


Copyright
=========

This document has been placed in the public domain.
