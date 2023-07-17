PEP: PyResource_Close() API

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

If a close callback function needs *extra* data to close a resource, it
should allocate a structure on a heap memory and store it as
``PyResource.data``. If the function creating a resource allocates a
memory block which should be released by the close callback, it can
allocate a larger memory block and stores these *extra* data before or
after data inside the memory block.

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
* ``const char* PyEval_GetFuncNameRes(PyObject *func, PyResource *res)``:
  safe variant of ``PyEval_GetFuncName()``.
* ``const char* PyUnicode_AsUTF8Res(PyObject *unicode, PyResource *res)``:
  safe variant of ``PyUnicode_AsUTF8()``.
* ``const char* PyUnicode_AsUTF8AndSizeRes(PyObject *unicode, Py_ssize_t *psize, PyResource *res)``:
  safe variant of ``PyUnicode_AsUTF8AndSize()``.
* ``const char* PyCapsule_GetNameRes(PyObject *capsule, PyResource *res)``:
  safe variant of ``PyCapsule_GetName()``.

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

  * ``PyUnicode_GetDefaultEncoding()`` (``const char*``)
  * ``PyImport_GetMagicTag()`` (``const char*``)
  * ``Py_GetVersion()`` (``const char *``)
  * ``Py_GetPlatform()`` (``const char *``)
  * ``Py_GetCopyright()`` (``const char *``)
  * ``Py_GetCompiler()`` (``const char *``)
  * ``Py_GetBuildInfo()`` (``const char *``)
  * ``PyHash_GetFuncDef()`` (``PyHash_FuncDef*``)

* Thread local storage:

  * ``PyThread_tss_get()`` (``void*``)
  * ``PyThread_get_key_value()`` (``void*``)

* Misc functions:

  * ``PyBuffer_GetPointer()`` (``void*``): the caller must call
    ``PyBuffer_Release()``.
  * ``PyCapsule_Import()`` (``void*``):
    the caller must hold a reference to the capsule object.
  * ``Py_GETENV()`` and ``Py_GETENV()`` (``char*``):
    the pointer becomes invalid if environment variables are changed.
  * ``PyType_GetSlot()`` (``void*``):
    the caller must hold a reference to the type object.
  * ``PyModule_GetState()`` (``void*``):
    the caller must hold a reference to the module object.
  * ``PyType_GetModuleState()`` (``void*``):
    the caller must hold a reference to the module object of the type
    object.

* Deprecated functions, planned for removal:

  * ``Py_GetExecPrefix()`` (``wchar_t*``)
  * ``Py_GetPath()`` (``wchar_t*``)
  * ``Py_GetPrefix()`` (``wchar_t*``)
  * ``Py_GetProgramFullPath()`` (``wchar_t*``)
  * ``Py_GetProgramName()`` (``wchar_t*``)
  * ``Py_GetPythonHome()`` (``wchar_t*``)
