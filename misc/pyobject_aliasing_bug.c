/* Alias bug, gcc 8.2.1:

$ gcc -O2 -Wstrict-aliasing bug.c -Wall -o bug
bug.c: In function 'main':
bug.c:27:32: warning: dereferencing type-punned pointer will break strict-aliasing rules [-Wstrict-aliasing]
 #define TYPE(ob)             (((PyObject*)(ob))->ob_type)
                               ~^~~~~~~~~~~~~~~~
bug.c:51:27: note: in expansion of macro 'TYPE'
     const char *tp_name = TYPE(&item)->tp_name;
                           ^~~~
*/
#include <stdio.h>
#include <stddef.h>
#include <stdlib.h>

typedef ssize_t Py_ssize_t;

#undef Py_TRACE_REFS

#ifdef Py_TRACE_REFS
#define _PyObject_HEAD_EXTRA            \
    struct _object *_ob_next;           \
    struct _object *_ob_prev;
#else
#define _PyObject_HEAD_EXTRA
#endif

typedef struct _object {
    _PyObject_HEAD_EXTRA
    Py_ssize_t ob_refcnt;
    struct _typeobject *ob_type;
} PyObject;

typedef struct _typeobject {
    const char *tp_name;
} PyTypeObject;

#define TYPE(ob)             (((PyObject*)(ob))->ob_type)

PyTypeObject*
new_type(void)
{
    PyTypeObject *type = malloc(sizeof(PyTypeObject));
    type->tp_name = "tp_name";
    return type;
}


PyObject*
new_object(void)
{
    PyObject *obj = malloc(sizeof(PyObject));
    obj->ob_type = new_type();
    return obj;
}

#define _PyObject_CAST(obj) ((PyObject*)( ((PyObject*)(obj))->ob_type ))

int main(void)
{
    PyObject *item = new_object();
    /* Correct bug: TYPE(item)->tp_name */
    const char *tp_name = TYPE(&item)->tp_name;
    printf("tp_name = %s\n", tp_name);
    return 0;
}
