PEP: xxx
Title: Python compatibility version
Author: Victor Stinner <vstinner@python.org>
Status: Draft
Type: Standards Track
Content-Type: text/x-rst
Created: 16-Oct-2019
Python-Version: 3.9


XXX Open Questions XXX
======================

* Well, first of all: do we want this? :-)
* Do we need command line option and environment variable for these
  features? In addition to the 3 new ``sys`` module functions.
* Do we want the parser (grammar) to handle the backward compatibility?
* Is it possible to modify the Python parser to support multiple
  versions of the Python grammars? AST and grammar are hardcoded to a
  single Python version. ``compile()`` has an undocumented
  ``_feature_version`` to not consider ``async`` and ``await`` as
  keywords.
* Parser and ``cache_tag``: regular users cannot write ``.pyc`` files
  into system directories. For example, users cannot write write
  ``/usr/lib64/python3.9/__pycache__/os.cpython-39-380.pyc`` on Linux.
  Basically, the optimization of precompiled ``.pyc`` files lost.


Abstract
========

Add ``sys.set_python_compat_version(version)`` to request Python 3.9 to
behave as Python 3.8.

Add ``sys.get_python_compat_version()`` and modify the standard library
to use it in some places to provide Python 3.8 compatibility on demand.

Add ``sys.set_python_min_compat_version(version)`` to prevent code to
request compatibility with Python older than *version*.
``sys.set_python_compat_version(old_version)`` raises an exception in
this case.

By default, ``sys.get_python_compat_version()`` is the current Python
version, and the minimum compatibility version is set to Python 3.0.


Rationale
=========

The need to evolve frequently
-----------------------------

To remain relevant and useful, Python has to evolve frequently. Some
enhancements require backward incompatible changes. Any backward
compatibility change can break an unknown number of projects which can
prevent developers to implement some features.

Users want to get the latest Python version to get new features and
better performance. A few backward incompatible changes prevent users to
use their applications on the latest Python version.

This PEP proposes to add a partial compatibility with old Python
versions as a tradeoff to fit both use cases.


Minimize the Python maintenance burden
--------------------------------------

While technically it is possible to provide a full compatibility with
old Python versions, this PEP proposes to minimize the number of
functions handling backward compatibility to reduce the maintenance
burden.

Each compatibility change should be properly discussed to estimance the
maintenance cost in the long-term.

At each Python release, compatibility code for old Python versions will
be removed. Each compatibility function can have a different support
depending on its maintenance cost and the estimated number of impacted
projects if it's removed.

The maintenance is not only on the code to implement the backward
compatibility, but also on the additional tests to check that it's not
broken.


Cases excluded from backward compatibility
------------------------------------------

The performance overhead of a compatibility layer must be small or even
not significant when it's not used.

The C API is out of the scope of this PEP: Py_LIMITED_API and the stable
ABI are already solving this problem. See the `PEP 384: Defining a
Stable ABI <https://www.python.org/dev/peps/pep-0384/>`_.

Security fixes which break the backward compatibility on purpose will
not get a compatibility layer. Security matters more than compatibility.
For example, ``http.client.HTTPSConnection`` was modified in Python
3.4.3 to performs all the necessary certificate and hostname checks by
default. It was a deliberate change motivated by the `PEP 476: Enabling
certificate verification by default for stdlib http clients
<https://www.python.org/dev/peps/pep-0476/>`_ (`bpo-22417
<https://bugs.python.org/issue22417>`_).

Changes which are not clearly backward incompatible are not covered by
this PEP. For example, the default protocol in the ``pickle`` module is
now Protocol 4 in Python 3.9, first introduced in Python 3.4. This
change is backward compatible up to Python 3.4.


Update your project to a newer Python
-------------------------------------

Without backward compatibility, all backward incompatible changes must
be fixed at once, which can be a blocker issue. It is even worse when
the old Python is separated by multiple releases from the newer Python.

Postponing an upgrade only makes things worse: each skipped release will
add more backward incompatible changes. The technical debt can only
increase.

With backward compatibility, it becomes possible to upgrade Python
increamentally in a project, without having to fix all issues at once.

The "all-or-nothing" is a show-stopper to port large Python 2 code bases
to Python 3.


Cleanup old Python code and DeprecationWarning
----------------------------------------------

One of the `Zen of Python (PEP 20)
<https://www.python.org/dev/peps/pep-0020/>`_ motto is:

    There should be one-- and preferably only one --obvious way to do
    it.

When Python evolves, new ways emerge. ``DeprecationWarning`` are emitted
to suggest to use the new way, but many developers ignore these
warnings, which are silent by default (except in the ``__main__``
module: see the `PEP 565 <https://www.python.org/dev/peps/pep-0565/>_`).

Sometimes, supporting both ways has a minor maintenance cost, but
developers prefer to drop the old way to cleanup the code anyway. Such
kind of change is backward incompatible.

Adding an optional backward compatibility prevents to break applications
and allows to continue to do such cleanup.


Redistribute the maintenance burden
-----------------------------------

The backward compatibility better involves authors of backward
incompatible changes in the upgrade path.


Examples
========

collections ABC aliases
-----------------------

``collections.abc`` aliases to ABC classes have been removed from the
``collections`` module in Python 3.9, after being deprecated since
Python 3.3. For example, ``collections.Mapping`` no longer exists.

In Python 3.6, aliases were created by ``from _collections_abc import
*``.

In Python 3.7, a ``__getattr__()`` has been added to the ``collections``
module to emit a DeprecationWarning at the first access to an
attribute::

    def __getattr__(name):
        # For backwards compatibility, continue to make the collections ABCs
        # through Python 3.6 available through the collections module.
        # Note, no new collections ABCs were added in Python 3.7
        if name in _collections_abc.__all__:
            obj = getattr(_collections_abc, name)
            import warnings
            warnings.warn("Using or importing the ABCs from 'collections' instead "
                          "of from 'collections.abc' is deprecated since Python 3.3, "
                          "and in 3.9 it will stop working",
                          DeprecationWarning, stacklevel=2)
            globals()[name] = obj
            return obj
        raise AttributeError(f'module {__name__!r} has no attribute {name!r}')

Compatibility with Python 3.8 can be restore in Python 3.9 by adding
back the ``__getattr__()`` function, but only when backward
compatibility is requested::

    def __getattr__(name):
        if (sys.get_python_compat_version() < (3, 9)
           and name in _collections_abc.__all__):
            ...
        raise AttributeError(f'module {__name__!r} has no attribute {name!r}')


Deprecated open() "U" mode
--------------------------

Using the "U" mode of ``open()`` is deprecated since Python 3.4 and
emits a ``DeprecationWarning``.  The `bpo-37330
<https://bugs.python.org/issue37330>`_ proposes to drop this mode: raise
an exception if it's used.

This change is more in the "cleanup" category than change required to
enhance Python. A backward compatibility mode would be welcome here, it
is likely to be trivial to implement.


Backward incompatible changes
=============================

Python 3.7 to Python 3.8
------------------------

When Python has been upgraded from 3.7 to 3.8, the build of more than
200 packages failed in Fedora Rawhide for various reasons:

* ``PyCode_New()`` requires a new parameter: broke all Cython extensions
  (all projects distribute precompiled Cython code). Fedora packages
  have been fixed to force rebuilding all Cython extensions.
  This change has been reverted during the beta phase and a new function
  ``PyCode_NewWithPosOnlyArgs()`` was added instead.

* ``types.CodeType`` now requires an additional mandatory parameter.
  Python 3.8 added ``CodeType.replace()`` to help projects to no longer
  depend on the exact signature of the ``CodeType`` constructor.

* C extensions are no longer linked to libpython

* sys.abiflags changed from ``'m'`` to an empty string: ``python3.8m``
  program is gone for example.

* PyInterpreterState made opaque.

  * Blender:

    * https://bugzilla.redhat.com/show_bug.cgi?id=1734980#c6
    * https://developer.blender.org/D6038

* XML attribute order. bpo-34160.

  * coverage: https://bugs.python.org/issue34160#msg329612
  * docutils: https://sourceforge.net/p/docutils/bugs/359/
  * pcs: https://bugzilla.redhat.com/show_bug.cgi?id=1705475
  * python-glyphsLib: https://bugzilla.redhat.com/show_bug.cgi?id=1705391

* etc.

This PEP doesn't cover all cases. It doesn't handle backward
incompatibles in the C API nor in the build system for example.


Python 3.6 to Python 3.7
------------------------

Example of Python 3.7 backward incompatible changes:

* ``async`` and ``await`` are now reserved keywords.
* Several undocumented internal imports were removed. One example is
  that ``os.errno`` is no longer available; use ``import errno``
  directly instead. Note that such undocumented internal imports may be
  removed any time without notice, even in micro version releases.


Micro releases
--------------

Sometimes, backward incompatible changes are introduced in micro
releases (``micro`` in ``major.minor.micro``) to fix bugs and security
vulnerabilities. Examples:

* Python 3.7.2, ``compileall`` and  ``py_compile`` module: the
  *invalidation_mode* parameter's default value is updated to ``None``;
  the ``SOURCE_DATE_EPOCH`` environment variable no longer
  overrides the value of the *invalidation_mode* argument, and
  determines its default value instead.

* Python 3.7.1, ``xml`` modules: the SAX parser no longer processes
  general external entities by default to increase security by default.

* Python 3.5.2, ``os.urandom()``: on Linux, if the ``getrandom()``
  syscall blocks (the urandom entropy pool is not initialized yet), fall
  back on reading ``/dev/urandom``.

* Python 3.5.1, ``sys.setrecursionlimit()``: a ``RecursionError``
  exception is now raised if the new limit is too low at the current
  recursion depth.

* Python 3.4.4, ``ssl.create_default_context()``: RC4 was dropped from
  the default cipher string.

* Python 3.4.3, ``http.client``: ``HTTPSConnection`` now performs all
  the necessary certificate and hostname checks by default.

* Python 3.4.2, ``email.message``: ``EmailMessage.is_attachment()`` is
  now a method instead of a property, for consistency with
  ``Message.is_multipart()``.

* Python 3.4.1, ``os.makedirs(name, mode=0o777, exist_ok=False)``:
  Before Python 3.4.1, if *exist_ok* was ``True`` and the directory
  existed, ``makedirs()`` would still raise an error if *mode* did not
  match the mode of the existing directory. Since this behavior was
  impossible to implement safely, it was removed in Python 3.4.1
  (`bpo-21082 <https://bugs.python.org/issue21082>`_).

Changes which are not backward compatible are also made in micro
releases. Examples:

* ``ssl.OP_NO_TLSv1_3`` constant was added to 2.7.15, 3.6.3 and 3.7.0
  for backwards compatibility with OpenSSL 1.0.2.
* ``typing.AsyncContextManager`` was added to Python 3.6.2.
* The ``zipfile`` module accepts a path-like object since Python 3.6.2.
* ``loop.create_future()`` was added to Python 3.5.2 in the ``asyncio``
  module.

Such changes don't need to be handled by the backward compatibility
proposd in this PEP.


Specification
=============

Add 3 functions to the ``sys`` module:

* ``sys.set_python_min_compat_version(min_version)``: Set the minimum
  compatibility version. ``sys.set_python_compat_version(old_version)``
  will raise an exception if ``old_version < min_version``.
  *min_version* must be greater than or equal to (3, 0).

* ``sys.set_python_compat_version(version)``: set the Python
  compatibility version. If it has been called previously, use the
  minimum of requested versions. If if is smaller than the minimum
  compatibility version, raise an exception.
  *version* must be greater than or equal to (3, 0).

* ``sys.get_python_compat_version()``: get the Python compatibility
  version.

A *version* must a tuple of 2 or 3 integers: ``(x, y)`` is equivalent to
``(x, y, 0)``.

By default, ``sys.get_python_compat_version()`` is the current Python
version.

Example to request compatibility with Python 3.8.0::

    import collections

    sys.set_python_compat_version((3, 8))

    # collections.Mapping alias removed in Python 3.9 is available
    # again, even if collections has been imported before calling
    # set_python_compat_version().
    class MyMapping(collections.Mapping):
        ...

Calling ``sys.set_python_compat_version(version)`` has no effect of the
code which has been executed previously.


The parser case and .pyc filenames
----------------------------------

The parser will produce a different output depending on the
compatibility version.

If the compatibility version is different than the current Python
version, the ``importlib`` module will change
``sys.implementation.cache_tag`` to include the compatibility version in
the ``.pyc`` filename.

Example. Python 3.9 uses ``'cpython-39'`` by default.
``sys.set_python_compat_version((3, 8))`` sets the ``cache_tag`` to
``'cpython-39-380'``.


Backwards Compatibility
=======================

Introducing ``sys.set_python_compat_version()`` function means that an
application will behave differently depending on the compatibility
version. Moreover, since the version can be decreased multiple times,
the application can behave differently depending on the import order.

Python 3.9 with ``sys.set_python_compat_version((3, 8))`` is not fully
compatible with Python 3.8: the compatibility is only partial.


Security Implications
=====================

Security fixes must be disabled by the backward compatibility.


Alternatives
============

Command line option and environment variable
--------------------------------------------

Don't add ``sys.set_python_compat_version(version)`` but add ``-X
compat_version=VERSION`` command line option and
``PYTHONMINVERSION=VERSION`` environment variable to set the minimum
version since the Python startup.

This alternative avoids to have a different behavior depending on
imported modules and the import order. The minimum verison cannot be
modified at runtime.

This alternative prevents to use the feature in module. It can only be
used on application. It is less convenient. For example, setuptools
entry points don't let to pass arbitrary command line options to Python.

Provide a workaround for each backward incompatible change
----------------------------------------------------------

``collections`` aliases::

    import collections.abc
    collections.Mapping = collections.abc.Mapping
    collections.Sequence = collections.abc.Sequence

``U`` mode for ``open()``::

    orig_open = builtins.open

    def python38_open(file, mode='r, *args, **kw):
        # ignore 'U' mode
        mode = mode.replace('U', '')
        return orig_open(file, mode, *args, **kw)

    builtins.open = python38_open

PyObject_GC_Track():

    There is no known workaround.

``async`` and ``await`` keywords:

    There is no known workaround.

parser: set compat_version per file
-----------------------------------

``sys.set_python_compat_version()`` doens't impact the parser. A special
statement to opt-in for an older Python syntax. It only impacts the
current file. For example::

    from __future__ import python35_syntax

    async = 1
    await = 2

It avoids the need to have one each ``.pyc`` file per ``compat_version``
per ``.py`` source file.

Temporary moratorium on backward incompatible changes
-----------------------------------------------------

In 2009, the PEP 3003 "Python Language Moratorium" proposed to a
temporary moratorium (suspension) of all changes to the Python language
syntax, semantics, and built-ins for Python 3.1 and Python 3.2.

In May 2018, during PEP 572 discussions, it was also proposed to slow
down Python changes: see the python-dev thread `Slow down...
<https://mail.python.org/archives/list/python-dev@python.org/thread/HHKRXOMRJQH75VNM3JMSQIOOU6MIUB24/#PHA35EAPNONZMTOYBINGFR6XXNMCDPFQ>`_.

`Barry Warsaw's call on this
<https://mail.python.org/archives/list/python-dev@python.org/message/XR7IF2OB3S72KBP3PEQ3IKBOERE4FV2I/>`_:

    I don’t believe that the way for Python to remain relevant and
    useful for the next 10 years is to cease all language evolution.
    Who knows what the computing landscape will look like in 5 years,
    let alone 10?  Something as arbitrary as a 10 year moratorium is
    (again, IMHO) a death sentence for the language.

Python LTS and release cycle changes
------------------------------------

XXX Elaborate the relationship with the two proposed PEPs.

PEP 602 -- Annual Release Cycle for Python
https://www.python.org/dev/peps/pep-0602/

PEP 605 -- A rolling feature release stream for CPython
https://www.python.org/dev/peps/pep-0605/


References
==========

The Perl programming language has an `use function
<https://perldoc.perl.org/functions/use.html>`_ to opt-in for backward
compatibility with an older Perl version. Example: ``use 5.24.1;``.


Copyright
=========

This document is placed in the public domain or under the
CC0-1.0-Universal license, whichever is more permissive.



..
   Local Variables:
   mode: indented-text
   indent-tabs-mode: nil
   sentence-end-double-space: t
   fill-column: 70
   coding: utf-8
   End:
