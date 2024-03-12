Headers::

    PEP: xxx
    Title: Make PyObject opaque
    Author: Victor Stinner <vstinner@python.org>
    Status: Draft
    Type: Standards Track
    Created: 12-Mar-2024
    Python-Version: 3.13

    .. highlight:: c

Abstract
========

Change the ABI to solve the problem of the different ``PyObject`` and
``PyVarObject`` layout between regular Python build and Free Threading
(PEP 703) build. This change makes it easier to ship a single binary
working on the two builds, but it only solves the problem of the
``PyObject`` problem, it doesn't solve all problems.


Rationale
=========

``PyObject`` and ``PyVarObject`` structures
-------------------------------------------

Until Python 3.11, the ``PyObject`` structure is simple, it has two
members: ``ob_refcnt`` (``Py_ssize_t``) and ``ob_type`` (``PyTypeObject*``),
that's it! The ``PyVarObject`` structure inherits from ``PyObject`` and adds
``ob_size`` member (``Py_ssize_t``).

Python 3.12 implemented `PEP 683 <https://peps.python.org/pep-0683/>`_
"Immortal Objects, Using a Fixed Refcount" which made `ob_refcnt` "a
little bit" more complex::

    #if (defined(__GNUC__) || defined(__clang__)) \
            && !(defined __STDC_VERSION__ && __STDC_VERSION__ >= 201112L)
        // On C99 and older, anonymous union is a GCC and clang extension
        __extension__
    #endif
    #ifdef _MSC_VER
        // Ignore MSC warning C4201: "nonstandard extension used:
        // nameless struct/union"
        __pragma(warning(push))
        __pragma(warning(disable: 4201))
    #endif
        union {
           Py_ssize_t ob_refcnt;
    #if SIZEOF_VOID_P > 4
           PY_UINT32_T ob_refcnt_split[2];
    #endif
        };
    #ifdef _MSC_VER
        __pragma(warning(pop))
    #endif

Python 3.13 has a new Free Threading build which implements `PEP 703
<https://peps.python.org/pep-0703/>`_ "Making the Global Interpreter
Lock Optional in CPython". This PEP keeps ``ob_type`` unchanged, but
makes reference counting way more complicated::

    struct _object {
        // ob_tid stores the thread id (or zero). It is also used by the GC and the
        // trashcan mechanism as a linked list pointer and by the GC to store the
        // computed "gc_refs" refcount.
        uintptr_t ob_tid;
        uint16_t _padding;
        struct _PyMutex ob_mutex;   // per-object lock
        uint8_t ob_gc_bits;         // gc-related state
        uint32_t ob_ref_local;      // local reference count
        Py_ssize_t ob_ref_shared;   // shared (atomic) reference count
        PyTypeObject *ob_type;
    };

## PyObject setters

Since Python 3.10, I'm working on making enforcing access to
``PyObject`` and ``PyVarObject`` members via abstractions. Python always
had ``Py_REFCNT()``, ``Py_TYPE()`` and ``Py_SIZE()`` macros to **get**
these members. I added APIs to **set** these members:

* Python 3.10: ``Py_SET_REFCNT()``
* Python 3.12: ``Py_SET_TYPE()``, ``Py_SET_SIZE()``

Note: ``Py_SET_TYPE()`` is special, it's a workaround for Windows MSVC
compiler which doesn't support setting directly the base type of a
static type at build time (the compiler fails to retrive some symbols),
so C extensions set the base type at runtime when the type is
initialized (before calling ``PyType_Ready()``).

I wrote `PEP 674 <https://peps.python.org/pep-0674/>`_ "Disallow using
macros as l-values" to disallow `Py_TYPE(obj) = new_type;` and
``Py_SIZE(obj) = new_size;`` but enforces usage of ``Py_SET_TYPE()`` and
``Py_SET_SIZE()``. While the whole PEP got rejected, it got an exception
for ``Py_TYPE()`` and then because I forgot to revert ``Py_SIZE()``
(merged before PEP 674 was proposed), it landed in Python 3.12.


Analysis of making PyObject empty
---------------------------------

One way to make the PyObject structure members opaque is to remove them.
An issue is that ``sizeof(PyObject)`` is used in a few places:

* ``PyType_Spec.basicsize`` of ``PyType_FromSpec()``.


Specificiation
==============

Summary
-------

* Remove ``PyObject`` structure members: enforce usage of functions to
  access them.
* Add internal ``_PyObject`` structure and move old ``PyObject`` members
  there.
* Allocate ``_PyObject`` before ``PyObject*`` pointer: in the
  "preheader" section.
* Implement ``Py_INCREF()`` and ``Py_DECREF()`` as function calls.
* ``PyType_FromSpec()`` will overallocate object to not break the stable
  ABI.

Make PyObject structure empty
-----------------------------

The PyObject structure becomes empty::

    typedef struct {
        // empty
    } PyObject;

It means that ``sizeof(PyObject)`` becomes ``0`` bytes.

Members are moved to a new internal ``_PyObject`` structure. Example::

    typedef struct {
        Py_ssize_t ob_refcnt;
        PyTypeObject *ob_type;
    } _PyObject;

The real ``_PyObject`` structure is more complicated with PEP 683 and
PEP 703.

PyObject before PyObject* pointer
---------------------------------

Example of an instance of a heap type tracked by the garbage collector
with ``Py_TPFLAGS_PREHEADER`` flag. Layout::

    +-------------------+
    | <managed weakref> | <= MANAGED_WEAKREF_OFFSET
    | <managed dict>    | <= MANAGED_DICT_OFFSET
    +-------------------+
    | _gc_next          | <= PyGC_Header
    | _gc_prev          |
    +-------------------+
    | ob_refcnt         | <= Py_REFCNT() / Py_SET_REFCNT()
    | ob_type           | <= Py_TYPE()
    +-------------------+
    | Data              | <= PyObject*
    +-------------------+

Before ``PyObject*`` was pointing to ``ob_refcnt``. Now it points to
``Data``.

See also the ``_PyType_PreHeaderSize()`` function which computes the
size in bytes of data stored before the ``PyObject*`` pointer.

Py_INCREF() and Py_DECREF()
---------------------------

Py_INCREF(), Py_XINCREF(), Py_DECREF() and Py_XDECREF() functions are
now implemented as function calls. They are already implemented as
function calls in the limited C API version 3.12.

Thanks to that, C extensions use the same ABI for regular Python build
and Free Threading build for Py_INCREF() and Py_DECREF(): function
calls.


Backward Compatibility
======================

This PEP breaks the C API on purpose.

Accessing directly ``PyObject`` and ``PyVarObject`` members is no longer
possible: ``Py_REFCNT()``, ``Py_TYPE()`` and ``Py_SIZE()`` must be used
instead.

The stable ABI is not broken: ``PyType_FromSpec()`` overallocates memory
to not break the stable ABI. The only ABI change is ``sizeof(PyObject)``
and ``sizeof(PyVarObject)`` which become ``0`` bytes.


Prior Art
=========

* xxx: PEP 703 simpler plan to overallocate memory in the stable ABI
* xxx: Mark Shannon's plan
* Article: `Make structures opaque in the Python C API
  <https://vstinner.github.io/c-api-opaque-structures.html>`_ (March
  2021) by Victor Stinner.
* Article: `Python C API: Add functions to access PyObject
  <https://vstinner.github.io/c-api-abstract-pyobject.html>`_ (Oct 2021)
  by Victor Stinner.
* `PEP 620 <https://peps.python.org/pep-0620/>`_ "Hide implementation
  details from the C API" (June 2020) by Victor Stinner.
* Issue: `C API: Avoid accessing PyObject and PyVarObject members
  directly <https://github.com/python/cpython/issues/83754>`_
  (February 2020) by Victor Stinner.
