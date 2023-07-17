PEP: PyResource_Close() API

Abstract
========

Add ``PyResource`` structure and the following functions:

* ``PyResource_Close()``
* ``PyByteArray_AsStringRes()``
* ``PyBytes_AsStringRes()``
* ``PyCapsule_GetNameRes()``
* ``PyEval_GetFuncNameRes()``
* ``PyUnicode_AsUTF8AndSizeRes()``
* ``PyUnicode_AsUTF8Res()``

Rationale
=========

The Python C API has multiple functions returning pointers which are
direct access to an object content. The caller cannot notice Python when
it is done with this pointer. Usually, the pointer is expected to remain
valid until the object is finalized. Such API makes the assumption that
objects cannot move in memory (they are pinned in memory, their memory
address don't change) and that the caller is able to ensure that the
object is not finalized while the pointer is used.

One problem is that the Python C API does not document well which
functions can execute arbitrary Python code which can indirectly
finalize the object. For example, just a simple comparison like
``PyObject_RichCompare`` can execute arbitrary Python code, since it's
possible to override comparison methods in Python, like ``__eq__()``.

If the object is finalized, the pointer becomes a dangling pointer and
the C extension can crash or not depending if the memory was reused or
not, and if the pointer can still be deferenced or not. The behavior is
not deterministic which makes such bug harder to detect and to fix.

Such API prevents to change Python internals. For example, currently the
``PyUnicode_AsUTF8()`` function does cache the UTF-8 encoded string
inside the Python string object. It prevents to remove the cache. If a
new API using a "close callback" is added, once the old API is removed,
it becomes possible to no longer cache the encoded string: encode the
string at each call.

This problem is similar to use the usage of borrowed references to
Python objects. For borrowed references, an easy fix is to provide a new
API which returns a strong reference instead. The problem of borrowed
references is outside the scope of this PEP.

XXX avoid exposing multiple "free" functions such as (now removed)
private ``_Py_FreeCharPArray()`` function which was used by
``_PySequence_BytesToCharpArray()``.

XXX relationship with ``PyBuffer_Release()``.

XXX similar APIs

* Unix file descriptor: ``close(fd)``
* Windows ``HANDLE``: ``CloseHandle(handle)``
* HPy handle: ``HPy_Close(handle)``

XXX old APIs

* Python 2 PyObject_AsCharBuffer(), PyObject_AsReadBuffer() and
  PyObject_AsWriteBuffer() return a pointer which can later become a
  dangling pointer: there is no "release" function.


Proposition
===========

PyResource API
--------------

API::

    typedef struct {
        void (*close_func) (void *data);
        void *data;
    } PyResource;

    PyAPI_FUNC(void) PyResource_Close(PyResource *res);

A new PyResource_Close() function is proposed so the owner of a resource
can report when it is done with a resource: when the resource can be
released. The function expects a pointer to a new ``PyResource``
structure which contains information to close the resource.

Since code can now be executed when a resource is closed, it becomes
possible to also execute code to create the resource and so provide a
safer API. For example, a variant of the ``PyUnicode_AsUTF8()`` function
can be added to hold a strong reference to the string, to make sure that
the pointer of the cached UTF-8 string remains valid until
``PyResource_Close()`` is called.

Depending on the code which should be executed in
``PyResource_Close()``, different "close callback" functions can be
used.

If a close callback function needs *extra* data to close a resource, it
should allocate a structure on a heap memory and store it as
``PyResource.data``. If the function creating a resource allocates a
memory block which should be released by the close callback, it can
allocate a larger memory block and stores these *extra* data before or
after data inside the memory block.

The ``PyResource`` should be avoided with the function which returns a
newly allocated string: the caller should just call a function to
release the memory in this case.

The ``PyResource_Close()`` implementation is simple::

    void PyResource_Close(PyResource *res)
    {
        if (res->close_func == NULL) {
            return;
        }
        res->close_func(res->data);
    }

Variants using PyResource
-------------------------

Add the following functions:

* ``const char* PyBytes_AsStringRes(PyObject *op, PyResource *res)``:
  safe variant of ``PyBytes_AsString()``.
* ``char* PyByteArray_AsStringRes(PyObject *self, PyResource *res)``:
  safe variant of ``PyByteArray_AsString()``.
* ``const char* PyCapsule_GetNameRes(PyObject *capsule, PyResource *res)``:
  safe variant of ``PyCapsule_GetName()``.
* ``const char* PyEval_GetFuncNameRes(PyObject *func, PyResource *res)``:
  safe variant of ``PyEval_GetFuncName()``.
* ``const char* PyUnicode_AsUTF8Res(PyObject *unicode, PyResource *res)``:
  safe variant of ``PyUnicode_AsUTF8()``.
* ``const char* PyUnicode_AsUTF8AndSizeRes(PyObject *unicode, Py_ssize_t *psize, PyResource *res)``:
  safe variant of ``PyUnicode_AsUTF8AndSize()``.

These variants hold a strong reference to the object and so the returned
pointer is guaranteed to remain valid until the resource is closed with
``PyResource_Close()``.

Functions left unchanged
------------------------

No variant is planned to be added for the following functions which
return pointers. Some functions are safe. For the unsafe functions,
variants using ``PyResource`` can be added later.

* The caller function must release the returned newly allocated memory
  block:

  * ``PyOS_double_to_string()``
  * ``PyUnicode_AsUTF8String()``
  * ``PyUnicode_AsWideCharString()``
  * ``Py_DecodeLocale()``, ``Py_EncodeLocale()``
  * Allocator functions like ``PyMem_Malloc()``

* Get static data:

  * ``PyUnicode_GetDefaultEncoding()``
  * ``PyImport_GetMagicTag()``
  * ``Py_GetVersion()``
  * ``Py_GetPlatform()``
  * ``Py_GetCopyright()``
  * ``Py_GetCompiler()``
  * ``Py_GetBuildInfo()``
  * ``PyHash_GetFuncDef()``

* Thread local storage:

  * ``PyThread_tss_get()``
  * ``PyThread_get_key_value()``

* Misc functions:

  * ``PyBuffer_GetPointer()``: the caller must call
    ``PyBuffer_Release()``.
  * ``PyCapsule_Import()``:
    the caller must hold a reference to the capsule object.
  * ``Py_GETENV()`` and ``Py_GETENV()`` (``char*``):
    the pointer becomes invalid if environment variables are changed.
  * ``PyType_GetSlot()``:
    the caller must hold a reference to the type object.
  * ``PyModule_GetState()``:
    the caller must hold a reference to the module object.
  * ``PyType_GetModuleState()``:
    the caller must hold a reference to the module object of the type
    object.

* Deprecated functions, planned for removal:

  * ``Py_GetExecPrefix()`` (``wchar_t*``)
  * ``Py_GetPath()`` (``wchar_t*``)
  * ``Py_GetPrefix()`` (``wchar_t*``)
  * ``Py_GetProgramFullPath()`` (``wchar_t*``)
  * ``Py_GetProgramName()`` (``wchar_t*``)
  * ``Py_GetPythonHome()`` (``wchar_t*``)

Links
=====

* https://github.com/python/cpython/issues/106592
* https://github.com/capi-workgroup/problems/issues/57
