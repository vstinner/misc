Goals
=====

* Stable ABI for everyone.
* Moving GC
* Performance scales better with the number of CPU cores
* Being able to change Python internals without having to worry
  about breaking any C extension

Milestones
==========

* Stage 1

  * More opaque structures
  * More getter functions
  * Less macros
  * Less macros abuses
  * UNLOCK:

    * Less broken projects when Python internals evolves
    * C API easier to use in C++ and Rust

* Stage 2

  * All structures are opaque
  * ABI only made of function calls
  * UNLOCK: stable ABI for everyone

* Stage 3

  * ``PyObject*`` cannot be dereference: PyObject is opaque
  * Explicit resource management in the API (get/release)
  * Get rid of reference counting inside Python; public C API can still
    use reference counting (or handles)
  * UNLOCK: moving GC, performance scales with the number of CPU cores

Tasks
=====

* DONE: PEP 670 (step 1): Convert macros to functions
* WIP: PEP 670 (step 2): Convert static inline functions to regular functions
* WIP: PEP 674: Disallow using macros as l-values
* TODO: Remove ``PyTypeObject`` members

  * Move more C extensions towards heap types: use ``PyType_FromSpec()``
  * Replace ``type->tp_xxx`` with ``PyType_GetSlot(type, Py_tp_xxx)``
  * Add Py_buffer support to heap types

* TODO: Remove all structure members from the API, PyObject will be the last

  * DONE: ``PyInterpreterState`` (3.8), ``PyGC_Head`` (3.9),
    ``PyFrameObject`` (3.11)
  * WIP: ``PyObject``, ``PyVarObject`` (Python 3.11; PEP 670, PEP 674)
  * WIP: ``PyCodeObject``, ``PyThreadState``

* TODO: Avoid sizeof() in the API/ABI
* TODO: Design a new API with explicit resource management

  * Use ``Py_buffer``?
  * Creating a view can copy data or pin the object in memory
  * Need a "release" operation
  * ``ptr = PyBytes_AsString(bytes)``
  * ``array = &PyTuple_GET_ITEM(tuple, 0)``

* Maybe replace types like ``PyBytesObject*`` with ``PyObject*`` in
  the C API and ``PyBytesObject`` would become an alias to ``PyObject``.
  All structures will be empty anyway.

* ???: Get rid of borrowed references in the API

  * PyDict_GetItem()
  * PyTuple_GetItem()
  * PyErr_Occurred()
  * PyWeakref_GetObject()
  * etc.

Constraints
===========

* Provide documentation and tools to ease the migration;
  pythoncapi-compat is a first working tool
* Reduce the number of broken projects per Python release;
  projects can be adapted before the incompatible change is introduced
* If possible, avoid introducing new compiler warnings.
