XXX https://github.com/hpyproject/hpy/wiki/next-level

+++++++++++++++++++++++++++++++++++++++++++
Add abstractions to access C API structures
+++++++++++++++++++++++++++++++++++++++++++

Abstract
========

Motivation
==========

Access directly structure members
---------------------------------

Core structures like PyObject and PyTupleObject are exposed in the
public C API and are accessed directly. For example, it's common to get
an object type name with ``ob->ob_type->tp_name``: get an object type
directly by reading the ``PyObject.ob_type`` member. At the ABI level,
it is fine to access directly structure members for best perforamnces.

At the API level, it would better to add abstraction: add an indirection
to avoid developers accessing directly structure members.

Other Python implementations
----------------------------

Python implementations other than CPython should implement the C API to
support popular C extensions like numpy or psycopg2.

PyPy emulates the C API by converting PyPy objects to CPython objects
using CPython structures like PyObject or PyTupleObject.

There are now other Python implementations like:
`Pyston <https://www.pyston.org/>`_,
`Facebook Cinder <https://github.com/facebookincubator/cinder>`_
and `Facebook Skybison <https://github.com/facebookexperimental/skybison>`_.

Examples of past C API incompatible changes
===========================================

Changes in structures between Python 3.3 and Python 3.11 which caused
API and ABI issues:

* PyFrameObject
* PyGC_Head
* PyMemoryViewObject
* PyThreadState
* PyTypeObject

Python 3.4 Py_TPFLAGS_HAVE_FINALIZE flag
----------------------------------------

In Python 3.4, the PEP 442 "Safe object finalization" added the
tp_finalize member at the end of the PyTypeObject structure. For ABI
backward compatibility, a new Py_TPFLAGS_HAVE_FINALIZE type flag was
required to announce if the type structure contains the tp_finalize
member. The flag was removed in Python 3.8 (bpo-32388).

Other "HAVE" flags:

* Py_TPFLAGS_HAVE_VERSION_TAG
* Py_TPFLAGS_HAVE_AM_SEND

bpo-42747: Remove Py_TPFLAGS_HAVE_AM_SEND and make
Py_TPFLAGS_HAVE_VERSION_TAG no-op (Python 3.11):
https://github.com/python/cpython/commit/a4760cc32d9e5dac7be262e9736eb30502cd7be3

Python 3.5 PyMemoryViewObject.format
------------------------------------

The undocumented ``format`` member of the (non-public)
PyMemoryViewObject structure has been removed. All extensions relying on
the relevant parts in ``memoryobject.h`` must be rebuilt.

PyGC_Head and memory alignment
------------------------------

* https://bugs.python.org/issue33597
* https://bugs.python.org/issue39599
  ABI breakage between Python 3.7.4 and 3.7.5: change in PyGC_Head structure
* https://bugs.python.org/issue40241
  [C API] Make PyGC_Head structure opaque, or even move it to the internal C API
* https://bugs.python.org/issue27987
  obmalloc's 8-byte alignment causes undefined behavior

Python 3.5::

    typedef union _gc_head {
        struct {
            union _gc_head *gc_next;
            union _gc_head *gc_prev;
            Py_ssize_t gc_refs;
        } gc;
        double dummy;  /* force worst-case alignment */
    } PyGC_Head;

Python 3.7::

    typedef union _gc_head {
        struct {
            union _gc_head *gc_next;
            union _gc_head *gc_prev;
            Py_ssize_t gc_refs;
        } gc;
        long double dummy;  /* force worst-case alignment */
        // malloc returns memory block aligned for any built-in types and
        // long double is the largest standard C type.
        // On amd64 linux, long double requires 16 byte alignment.
        // See bpo-27987 for more discussion.
    } PyGC_Head;

Python 3.11::

    typedef struct {
        // Pointer to next object in the list.
        // 0 means the object is not tracked
        uintptr_t _gc_next;

        // Pointer to previous object in the list.
        // Lowest two bits are used for flags documented later.
        uintptr_t _gc_prev;
    } PyGC_Head;

ABI issue.

Python 3.7 _PyErr_StackItem exc_state
-------------------------------------

Python 3.7: to fix https://bugs.python.org/issue25612

* PyFrameObject: Remove ``f_exc_type``, ``f_exc_value``and
  ``f_exc_traceback`` members.
* PyThreadState: Replace ``exc_type``, ``exc_value`` and
  ``exc_traceback`` members with a new ``exc_state`` member.
* PyGenObject: Add ``gi_exc_state`` member.
* PyCoroObject: Add ``cr_exc_state`` member.

https://github.com/python/cpython/commit/ae3087c6382011c47db82fea4d05f8bbf514265d

Python 3.8 PyInterpreterState
-----------------------------

The PyInterpreterState structure was made opaque in Python 3.8
(bpo-35886).

Python 3.9 PyTypeObject.tp_print
--------------------------------

The PyTypeObject.tp_print member, deprecated since Python 3.0 released
in 2009, has been removed in the Python 3.8 development cycle. But the
change broke too many C extensions and had to be reverted before 3.8
final release. Finally, the member was removed again in Python 3.9.

The PyTypeObject structure is one which evolved the most in the C API.
Over the years, it got new fields. In Python 3.9, the ``tp_print``
member has been removed. Cython generated C code setting ``tp_print`` to
0, like: ``FooType.tp_print = 0;``.

In Python 3.8, a new ``tp_vectorcall`` member was added before tp_print
in the structure, and tp_print was kept but marked as deprecated::

    typedef struct _typeobject {
        ...
        vectorcallfunc tp_vectorcall;

        /* bpo-37250: kept for backwards compatibility in CPython 3.8 only */
        Py_DEPRECATED(3.8) int (*tp_print)(PyObject *, FILE *, int);
        ...
    } PyTypeObject;

The practical problem is that updating Cython to no longer generate code
like ``FooType.tp_print = 0;`` is not enough. Most projects publish
C code generated by Cython when they distribute the source code of their
project to avoid depending on Cython. As a consequence, projects must
re-generate the C code with an updated Cython and then publish a new
version to be compatible with the newer C API (without ``tp_print``).

Python 3.9: opaque PyGC_Head
----------------------------

The PyGC_Head structure is now opaque (bpo-40241).

Python 3.11 PyFrameObject.f_back
--------------------------------

In Python 3.11, ``PyFrameObject.f_back`` is now computed lazily. It can
be ``NULL`` even if there is a previous frame. The ``PyFrame_GetBack()``
function must now be called to get the previous frame properly.

Python 3.10 PyThreadState.use_tracing
-------------------------------------

Python 3.10 removes the ``use_tracing`` member of the PyThreadState
structure: open issue https://bugs.python.org/issue43760

Broken C extensions:

* dipy
* greenlet
* scikit-learn (code generated by Cython)
* smartcols
* yappi


Limited C API and the stable ABI
================================

The limited C API excludes the PyTypeObject structure which should not
leak into the stable ABI.

