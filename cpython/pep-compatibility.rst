++++++++++++++++++++++++++++
Python Compatibility Version
++++++++++++++++++++++++++++

Use Cases
=========

Use Case: Stability
-------------------

Users want to update Python to get security fixes, but don't have
the time budget to update the source code of their projects.

The compatibility version gives them more time to update their project,
rather than being pressured by the PEP 387 delay of 2 years.

DRAWBACK: keep compatibility code "forever".

Use Case: Evolve Python
-----------------------

Python core developers have to introduce incompatible changes to
introduce new features, or sometimes just to cleanup deprecated
functions to make Python more consistent.

The compatibility version makes core developers more relaxed to make
incompatible changes since users now have a way to opt-in for the old
behavior.

Deprecation process
===================

* Deprecated in the documentation
* Emit PendingDeprecationWarning
* Emit DeprecationWarning
* Compatibility version
* Remove the function

Time:

* Deprecated: 2 Python releases (2 years)
* Compatibility:

  * Python 3.12 drops support for Python 3.6 compatibility?
  * Python 4.0 drops support for Python 3.6 compatibility?
  * Never remove compatibility?
  * 10 years? 20 years?

Compatibility
=============

* Deprecated collections.MutableMapping aliases (Python 3.10)
* open() "U" mode (Python 3.11)
* unittest.TestCase deprecated methods (Python 3.11)
* ``@asyncio.coroutine`` (Python 3.11)
* Deprecated inspect.getargspec(), inspect.formatargspec() (Python 3.11)

A compatibility function should not be added if it requires developers
to test ``sys.version_info`` **and** ``sys.compatibilty_version`` to
check what is the running Python behavior.

How many behavior?

* Python 3.10
* Python 3.11
* Python 3.11 with compatibility with Python 3.10

``hasattr()`` is a good way to test if Python has a feature. For
example, test ``hasattr(collections, 'MutableMapping')``.

Not supported
=============

* Add removed stdlib module.
* types.CodeType constructor
* C API changes
* Different Python grammar like Python 3.7 ``async`` and ``await``
  keywords. It would require to change PYC filenames, it's too
  complicated rather it's rare that grammar changes affect many
  projects. Suporting different grammar can be considered later if
  the situation evolves.
