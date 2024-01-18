PEP headers::

    PEP: xxx
    Title: Python configuration C API
    Author: Victor Stinner <vstinner@python.org>
    Discussions-To: https://discuss.python.org/t/pep-737-unify-type-name-formatting/39872
    Status: Draft
    Type: Standards Track
    Created: 29-Nov-2023
    Python-Version: 3.13
    Post-History: `29-Nov-2023 <https://discuss.python.org/t/pep-737-unify-type-name-formatting/39872>`__

Abstract
========

xxx


Rationale
=========

When first versions of `PEP 587 "Python Initialization Configuration"
<https://peps.python.org/pep-0587/>`_ were discussed, there was a
private field, for internal use only, ``_config_version`` (``int``): the
configuration version, used for ABI compatibility. It was decided that
if an application embeds Python, it sticks to a Python version, and so
there is no need to bother with the ABI compatibility.

The final PyConfig API of PEP 587 is excluded from limited C API since
it's main ``PyConfig`` structure is not versioned. Python cannot
guarantee ABI backward and forward compatibility, it's incompatible with
the stable ABI.

Since PyConfig was added to Python 3.8, the limited C API and the stable
ABI are getting more popular. For example, Rust bindings such as the
`PyO3 project <https://pyo3.rs/>`_ target the limited C API to embed
Python in Rust.

Also, the legacy API has been removed since Python 3.8:

* Global configuration variables such as ``Py_VerboseFlag``.
* Get the configuration such as ``Py_GetPath()``.
* Set the configuration such as ``Py_SetPath()``.

PEP 587 has no API to **get** the **current** configuration, only to
**configure** the Python **initialization**.

For example, the global configuration variable
``Py_UnbufferedStdioFlag`` was deprecated in Python 3.12 and using
``PyConfig.buffered_stdio`` is recommended instead. It only works to
configure Python, there is no public API to get
``PyConfig.buffered_stdio``.


Specification
=============

Get current configuration
-------------------------

``PyObject* PyConfig_Get(const char *name)``:

    Get the current value of a Python configuration option as an object.

    * Return a new reference on success.
    * Set an exception and return ``NULL`` on error.

``int PyConfig_GetInt(const char *name, int *value)``:

    Similar to ``PyConfig_Get()``, but return an integer.

    * Set ``*value`` and return ``0`` success.
    * Set an exception and return ``-1`` on error.


Configure the Python initialization
-----------------------------------

``PyInitConfig`` structure:

    Opaque structure to configure the Python initialization.

``PyInitConfig* PyInitConfig_Python_New(void)``:

    Create a new initialization configuration using Python Configuration
    default values.

    It must be freed ``PyInitConfig_Free()``.

    Return ``NULL`` on memory allocation failure.

``PyInitConfig* PyInitConfig_Isolated_New(void)``:

    Similar to ``PyInitConfig_Python_New()``, but use Isolated
    Configuration default values.

``void PyInitConfig_Free(PyInitConfig *config)``:

    Free memory of an initialization configuration.


``int PyInitConfig_SetInt(PyInitConfig *config, const char *name, int64_t value)``:

    Set an integer configuration option.

    * Return ``0`` on success.
    * Set an error in *config* and return ``-1`` on error.

``int PyInitConfig_SetStr(PyInitConfig *config, const char *name, const char *value)``:

    Set a string configuration option from a null-terminated bytes
    string.

    The bytes string is decoded by ``Py_DecodeLocale()``. If Python is
    not yet preinitialized, this function preinitializes it to ensure
    that encodings are properly configured.

    * Return ``0`` on success.
    * Set an error in *config* and return ``-1`` on error.

``int PyInitConfig_SetWStr(PyInitConfig *config, const char *name, const wchar_t *value)``:

    Set a string configuration option from a null-terminated wide
    string.

    If Python is not yet preinitialized, this function preinitializes
    it.

    * Return ``0`` on success.
    * Set an error in *config* and return ``-1`` on error.

``int PyInitConfig_SetStrList(PyInitConfig *config, const char *name, size_t length, char * const *items)``:

    Set a string list configuration option from an array of
    null-terminated bytes strings.

    The bytes string is decoded by :c:func:`Py_DecodeLocale`. If Python
    is not yet preinitialized, this function preinitializes it to ensure
    that encodings are properly configured.

    * Return ``0`` on success.
    * Set an error in *config* and return ``-1`` on error.

``int PyInitConfig_SetWStrList(PyInitConfig *config, const char *name, size_t length, wchar_t * const *items)``:

    Set a string list configuration option from a null-terminated wide
    strings.

    If Python is not yet preinitialized, this function preinitializes
    it.

    * Return ``0`` on success.
    * Set an error in *config* and return ``-1`` on error.

``int Py_InitializeFromInitConfig(PyInitConfig *config)``:

    Initialize Python from the initialization configuration.

    * Return ``0`` on success.
    * Set an error in *config* and return ``-1`` on error.
    * Set an exit code in *config* and return ``-1`` on exit.

Error handling
--------------

``int PyInitConfig_Exception(PyInitConfig* config)``:

    Check if an exception is set in *config*:

    * Return non-zero if an error was set or if an exit code was set.
    * Return zero otherwise.

``int PyInitConfig_GetError(PyInitConfig* config, const char **err_msg)``:

   Get the *config* error message.

   * Set *\*err_msg* (UTF-8 encoded string) and return ``1`` if an error
     is set.
   * Set *\*err_msg* to ``NULL`` and return ``0`` otherwise.

``int PyInitConfig_GetExitCode(PyInitConfig* config, int *exitcode)``:

    Get the *config* exit code.

    * Set *\*exitcode* and return ``1`` if an exit code is set.
    * Return ``0`` otherwise.


``void Py_ExitWithInitConfig(PyInitConfig *config)``:

    Exit Python and free memory of a initialization configuration.

    If an error message is set, display the error message.

    If an exit code is set, use it to exit the process.

    The function does not return.


Example
=======

Set some options of different types to initialize Python::

    void init_python(void)
    {
        PyInitConfig *config = PyInitConfig_Python_New();
        if (config == NULL) {
            printf("Init allocation error\n");
            return;
        }

        if (PyInitConfig_SetInt(config, "dev_mode", 1) < 0) {
            goto error;
        }

        // Set a list of wide strings (argv)
        wchar_t *argv[] = {L"my_program"", L"-c", L"pass"};
        if (PyInitConfig_SetWStrList(config, "argv",
                                     Py_ARRAY_LENGTH(argv), argv) < 0) {
            goto error;
        }

        // Set a wide string (program_name)
        if (PyInitConfig_SetWStr(config, "program_name", L"my_program") < 0) {
            goto error;
        }

        // Set a list of bytes strings (xoptions)
        char* xoptions[] = {"faulthandler"};
        if (PyInitConfig_SetStrList(config, "xoptions",
                                    Py_ARRAY_LENGTH(xoptions), xoptions) < 0) {
            goto error;
        }

        if (Py_InitializeFromInitConfig(config) < 0) {
            Py_ExitWithInitConfig(config);
        }
        PyInitConfig_Free(config);
    }


Implementation
==============

* Issue: `No limited C API to customize Python initialization
  <https://github.com/python/cpython/issues/107954>`_
* PR: `Add PyInitConfig C API
  <https://github.com/python/cpython/pull/110176>`_
* PR: `Add PyConfig_Get() function
  <https://github.com/python/cpython/issues/107954>`_


Backwards Compatibility
=======================

Only new APIs are added.

Existing API is deprecated, removed or modified.

Discussions
===========

xxx


Copyright
=========

This document is placed in the public domain or under the
CC0-1.0-Universal license, whichever is more permissive.
