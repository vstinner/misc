++++++++++++++++++++++++++++++++
Don't add sys.path[0] by default
++++++++++++++++++++++++++++++++

History
=======

* Dec 2021: `bad magic number in 'six'
  <https://github.com/benjaminp/six/issues/359#issuecomment-996159668>`_.
  The VMware Perl SDK installation process created ``/usr/bin/six.pyc``.
* May 2020: `Python flag/envvar to not put current directory on sys.path (but don’t ignore PYTHONPATH)
  <https://discuss.python.org/t/python-flag-envvar-to-not-put-current-directory-on-sys-path-but-dont-ignore-pythonpath/4235>`_
* Mar 2018: `bpo-33053 <https://bugs.python.org/issue33053>`_:
  Avoid adding an empty directory to ``sys.path`` when running a module with
  ``-m``.
* Jun 2017: `[Python-ideas] Security: remove "." from sys.path?
  <https://mail.python.org/pipermail/python-ideas/2017-June/045842.html>`_
* Oct 2015: `CVE-2015-5652
  <https://www.cvedetails.com/cve/CVE-2015-5652/>`_ about malicious
  ``readline.pyd`` in the current directory on Windows.
* Mar 2014: Python 3.4 adds ``-I`` option: isolated mode.
* Oct 2012: `bpo-16202 <https://bugs.python.org/issue16202>`_:
  ``sys.path[0]`` security issues
* Oct 2012: Sage: `Python sys.path security risk
  <https://trac.sagemath.org/ticket/13579>`_. The Sage test suite is vulnerable
  to stdlib module overridden in ``/tmp`` directory like ``/tmp/socket.py``.
* Nov 2011: `bpo-13506 <https://bugs.python.org/issue13506>`_:
  IDLE sys.path does not contain Current Working Directory
* Nov 2011: `bpo-13475 <https://bugs.python.org/issue13475>`_:
  Add ``--mainpath``/``--nomainpath`` command line options to override
  ``sys.path[0]`` initialisation
* Nov 2011: debian-python:
  `Re: ImportError: No module named multiarray (is back)
  <https://lists.debian.org/debian-python/2011/11/msg00058.html>`_
* Jun 2011: `PEP 405 -- Python Virtual Environments
  <https://www.python.org/dev/peps/pep-0405/>`_. It adds the ``pyvenv.cfg``
  configuration file.
* Mar 2011: `PEP 395 -- Qualified Names for Modules
  <https://www.python.org/dev/peps/pep-0395/>`_
* Aug 2009: `[Python-Dev] Excluding the current path from module search path?
  <https://mail.python.org/pipermail/python-dev/2009-August/091360.html>`_
* Apr 2009: `bpo-5753 <https://bugs.python.org/issue5753>`_:
  CVE-2008-5983 python: untrusted python modules search path. It adds
  the `PySys_SetArgvEx()
  <https://docs.python.org/dev/c-api/init.html#c.PySys_SetArgvEx>`_ function
  to Python 2.6.6 and Python 3.1.3.
* Dec 2008: Python 3.0 is released with absolute imports by default
* May 2004: `bpo-946373 <https://bugs.python.org/issue946373>`_:
  Do not add directory of sys.argv[0] into sys.path
* Dec 2003: `PEP 328 -- Imports: Multi-Line and Absolute/Relative
  <https://www.python.org/dev/peps/pep-0328/>`_

Bikeshedding on the option name
===============================

Option:

* ``--path0`` and ``--nopath0``
* ``--mainpath`` and ``--nomainpath``
* ``-p`` and ``-P``

Notes
=====

Python 3.10 sys.path[0]
-----------------------

=====================  =================================
Command                ``sys.path[0]``
=====================  =================================
``python -m module``   ``os.getcwd()``
``python -c code``     ``''``
``python script.py``   ``os.path.realpath('script.py')``
REPL: ``python``       ``''``
=====================  =================================

XXX what if os.chdir() is called?

Python 3.X changed __file__ to make it absolute

Unix permissions
----------------

On Unix, modifying the standard library requires the administrator permission.
Python supports user directory which can be modified by the current user.

Windows administrator and DLL injection
---------------------------------------

The Windows installer installed Python 2.7 in ``C:\Python27`` by default which
can be modified by regular users. The Windows installer of Python 3 now
installs Python in ``C:\Program Files`` which can only be modified by the
administrator.

On Windows 8.1 and older, the Windows installer is vulnerable to DLL injection:
if a malicious DLL is created in the same download directory that the
Python installer, the DLL is loaded by the Windows installer.

Moreover, the installation of ``pip`` by the Windows installer can also loads
malicious DLL installed in of the ``PATH`` directories.

Emit a warning if
-----------------

* Add a warning when the script is in a world-writable directory:
  https://bugs.python.org/issue16202#msg172756

XXX sys.stdlib_module_names XXX

Unix shebang
------------

Multiple long options cannot be used.

Perl 5.26
---------

In May 2017, the Perl 5.26 release removes the current directory from the
default module search path: `Removal of the current directory (".") from @INC
<https://metacpan.org/release/XSAWYERX/perl-5.26.0/view/pod/perldelta.pod#Removal-of-the-current-directory-(%22.%22)-from-@INC>`_.

Python options controlling sys.path
===================================

* ``argv[0]`` of the C ``main()`` function: name and path of the Python program
* Command line options:

  * ``-s``: don't add the user site directory
  * ``-E``: ignore environment variables
  * ``-I``: isolated mode (imply ``-E -s``)

* Environment variables:

  * ``PATH`` (to get ``argv[0]`` absolute path)
  * ``PYTHONEXECUTABLE`` (macOS)
  * ``PYTHONHOME``
  * ``PYTHONNOUSERSITE``
  * ``PYTHONPATH``
  * ``PYTHONPLATLIBDIR``
  * ``__PYVENV_LAUNCHER__`` (macOS)

* Configuration files:

  * ``pybuilddir.txt``
  * ``python._pth``
  * ``pyvenv.cfg``

* On Windows, application paths in the registry under
  ``SoftwarePythonPythonCoreX.YPythonPath`` of ``HKEY_CURRENT_USER`` and
  ``HKEY_LOCAL_MACHINE`` (where ``X.Y`` is the Python version).

Moreover, a path is prepended to ``sys.path``: see: `Python 3.10 sys.path[0]`_.

See the `Python Path Configuration
<https://docs.python.org/dev/c-api/init_config.html#python-path-configuration>`_
for more details.


Use Cases
=========

Override stdlib module
----------------------

xxx

Override 3rd party module
-------------------------

xxx


