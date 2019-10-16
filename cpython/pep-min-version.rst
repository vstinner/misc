PEP: xxx
Title: Python minimum version
Author: Victor Stinner <vstinner@python.org>
Status: Draft
Type: Standards Track
Content-Type: text/x-rst
Created: 16-Oct-2019
Python-Version: 3.9


Abstract
========

Add ``sys.set_min_python_version(version)`` function to request Python
to behave as the specified older Python version.


Motivation
==========

XXX

[Clearly explain why the existing language specification is inadequate to address the problem that the PEP solves.]


Rationale
=========

The overall idea is to allow developers to continue to push backward
incompatible changes in Python **and** slowdown changes from the user
perspective. The idea is the same trend than the Python LTS (Long Time
Support) idea.

Most Linux distributions only provide a single Python version, so users
are stick to one version. The idea is to help distributors to update
Python more frequently and help them to provide multiple Python versions
(if they want) and reduce the number of broken applications.

During the transition between Python 2.7 and "Python 3" (the minor version
increased during the 10 years of co-existence), more and more users reported
that they like Python 2.7 for its stability, whereas Python 3 was a fast moving
language. Not only the Python language evolves, but also its standard library.
Each minor version comes with its set of backward incompatible changes. Some
are major (like Python 3.7 which made "async" and "await" keywords), some are
minor (ex: remove "os.errno").

Core developers tends to purity: fix old issues. Users want stability and have
enough time to upgrade to the latest Python version.

The Perl language has a `use function
<https://perldoc.perl.org/functions/use.html>`_ to opt-in for the behavior of
an older Perl version. Example: ``use 5.24.1;``.

This PEP proposes to add a similar ``use Python 3.8;`` statement to Python 3.9
to opt-in for Python 3.8 backward compatibility. Only a limited set of
functions will use it. The standard library can use
``sys.implementation.used_version`` to change its behavior. The parser might
also use it.

To reduce the Python maintenance burden, old Python versions will only be
supported for a limited amount of time. The exact support duration will be
decided on a case by case basis, depending on the cost of supporting the code.
If the special cases for a specific Python version is cheap to maintain,
we may support it longer.

Concrete example for ``use Python 3.8;``:

* Enable ``collections.abc`` aliases: https://bugs.python.org/issue37324
* Enable ``U`` mode for ``open()``: https://bugs.python.org/issue37330
* Don't call ``tp_traverse()`` in ``PyObject_GC_Track()``:
  https://bugs.python.org/issue38392

Moreover, sometimes the behavior changes in minor releases. To fix a bug
or a major design issue. Examples: XXX

Backward incompatible changes
-----------------------------

When Python has been upgraded from 3.7 to 3.7, the build of more than
200 packages failed for various reasons:

* PyCode_New() requires a new parameter: broke all Cython extensions
  (all projects distribute precompiled Cython code). Fedora packages
  have been fixed to force rebuilding all Cython extensions.

* types.CodeType now requires an additional mandatory parameter.
  Python 3.8 added CodeType.replace() to help projects to no longer
  depend on the exact signature of the CodeType constructor.

* C extensions are no longer linked to libpython

* sys.abiflags changed from ``'m'`` to an empty string: ``python3.8m``
  program is gone for example.

* etc.

This PEP doesn't cover all cases. It doesn't handle backward
incompatibles in the C API for example.


Specification
=============

Syntax::

    sys.set_min_python_version(version)

where version must a be tuple of 2 or 3 positive integers. Examples::

    # Python 3.7.2
    sys.set_min_python_version((3, 7, 2))

    # Python 3.8: it is equivalent of Python 3.8.0
    sys.set_min_python_version((3, 8))


Multiple use statements
-----------------------

If an application uses two modules which require two different Python versions,
the oldest version will be picked. ``sys.implementation.used_version`` is
updated dynamically. It means that the supported Python version depends on the
import order.

Example::

    # collections.abc doesn't exist here
    use Python 3.8;
    # collections.abc exists again


Impact on testing
-----------------

Introducing ``use`` statement means that an application will behave
differently depending on the chosen version. Moreover, since the version
can be decreased multiple times, the application will behave differently
depending on the import order.

Python 3.9 with ``sys.set_min_python_version((3, 8))`` is not the same
as Python 3.8.


The parser case and .pyc filenames
----------------------------------

XXX would it be possible to support multiple Python syntax versions in
a single Python version? AST and grammar are hardcoded to a single
Python version.

The parser will produce a different output depending on ``min_version``.
If ``min_version`` is used (different than the current Python version),
importlib will change ``sys.implementation.cache_tag`` to change the
``.pyc`` filenames, to include ``min_version``.

For example, Python 3.9 uses ``'cpython-39'`` by default, but the
``cache_tag`` becomes ``'cpython-380'`` for ``min_version=(3, 8)`` and
``'cpython-372'`` for ``min_version=(3, 7, 2)``.

Drawbacks:

* most ``.pyc`` variants
* Regular users cannot write ``.pyc`` into system directory (ex: cannot
  write ``/usr/lib64/python3.9/__pycache__/os.cpython-39-380.pyc``)
  and so precompiled files optimization is basically lost.



Backwards Compatibility
=======================

[Describe potential impact and severity on pre-existing code.]


Security Implications
=====================

Opt-in for an older Python version can reduce the Python security. It should
be taken in account each time a function is modified to support multiple
Python versions.


How to Teach This
=================

XXX

Alternatives
============

Command line option and environment variable
--------------------------------------------

Don't add ``sys.set_min_python_version(version)`` but add ``-X
min_version=VERSION`` command line option and
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

parser: set min_version per file
--------------------------------

``sys.set_min_python_version()`` doens't impact the parser. A special
statement to opt-in for an older Python syntax. It only impacts the
current file. For example::

    from __future__ import python35_syntax

    async = 1
    await = 2

It avoids the need to have one each ``.pyc`` file per ``min_version``
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

XXX

PEP 602 -- Annual Release Cycle for Python
https://www.python.org/dev/peps/pep-0602/

PEP 605 -- A rolling feature release stream for CPython
https://www.python.org/dev/peps/pep-0605/


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
