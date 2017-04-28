#!/usr/bin/env python
"""
Small program to manage multiple Mercurial and Git repositories with a single
command. Most commands revert local changes and restore them when the command
is done. Ask for confirmation when a command will remove an important file or
remove local changes.

Commands:

 - diff [FILES]: show local differences
 - info: information on a repository (revision, branch, url, has local changes,
   etc.)
 - status or st: list new, modified and removed files
 - branches: list branches
 - tags: list tags
 - grep PATTERN: search a pattern in all files tracked by the SCM
 - files: list files tracked by the SCM
 - out: list local commits
 - add: add one or more files
 - commit|ci [files]: check in changes
 - histedit REVISION: rewrite the history
 - revert [FILES]: restore files in the last version
 - tag_contains REV: list tags containg the revision REV
 - stash: revert local changes and put them in a patch file
 - unstash: restore local changes reverted by the stash command
 - pull: download new commits and rebase local commits
 - push: pull + push local commits
 - clone: clone repositories listed in the scm_config configuration file
 - scan: discover all repositories from the current directory
 - clean: remove temporary and generated files
 - remove_untracked: remove files not tracked by the SCM,
   but keep ignored files
 - distclean: remove all files not tracked by the SCM

Programs needed at runtime:

 - patch
 - hg
 - git
 - grep

Distributed under the GNU GPL license version 3 or later.

See also:

- http://kitenet.net/~joey/code/mr/
- http://myrepos.branchable.com/
- https://streakycobra.github.io/gws/
"""
from __future__ import with_statement, print_function
import contextlib
import os
import re
import shutil
import subprocess
import sys
try:
    # Python 3
    from configparser import RawConfigParser, NoSectionError
    from io import StringIO
    raw_input = input
except ImportError:
    # Python 2
    from ConfigParser import RawConfigParser, NoSectionError
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO
if sys.hexversion >= 0x03030000: # Python 3.3 or later
    import shlex
from shutil import rmtree

CLEAN_SUFFIXES = ('.orig', '.rej', '.bak', '.pyc', '.pyo')

COLORS = "always" if sys.stdout.isatty() else 'never'
#COLORS = "always"
assert COLORS in ("always", "never")
STATUS_IGNORE_EXT = ".swp"
STATUS_IGNORE_FILES = set(("tags",))
DISTCLEAN_EXCLUDED_DIRS = ('.git', '.hg')

PATCH_PROGRAM = 'patch'
GREP_PROGRAM = 'grep'
HG_PROGRAM = 'hg'
GIT_PROGRAM = 'git'

ALL_COMMANDS = (
    "diff [FILES], info, status or st, branch, branches, tags, grep PATTERN, files, out",
    "add, commit|ci [files], histedit REVISION, revert [FILES], stash, unstash",
    "tag_contains REVISION",
    "pull, push",
    "clone, scan, clean, distclean, remove_untracked")
CONFIG_FILENAME = "scm_config"
STASH_FILENAME = 'stash'

GREP = (GREP_PROGRAM, '-R', '-I', '-H', '-n', '--color=%s' % COLORS)

HG_PULL = (HG_PROGRAM, 'pull', '--rebase')
HG_HISTEDIT = (HG_PROGRAM, 'histedit')
HG_REVERT = (HG_PROGRAM, 'revert', '--no-backup', '--rev', '.')
HG_UPDATE = (HG_PROGRAM, 'update')
HG_UPDATE_CLEAN = (HG_PROGRAM, 'update', '--clean')
HG_ADD = (HG_PROGRAM, 'add')
HG_DIFF = (HG_PROGRAM, 'diff')
HG_COMMIT = (HG_PROGRAM, 'commit')
HG_REVERT_ALL = (HG_PROGRAM, 'revert', '--all', '--no-backup')
HG_STATUS = (HG_PROGRAM, 'status')
HG_OUT = (HG_PROGRAM, 'out')
HG_CLONE = (HG_PROGRAM, 'clone')
HG_PUSH = (HG_PROGRAM, 'push')
HG_BRANCH = (HG_PROGRAM, 'branch')
HG_LIST_BRANCHES = (HG_PROGRAM, 'branches')
HG_LIST_TAGS = (HG_PROGRAM, 'tags')

GIT_PULL = ('pull', '--rebase')
GIT_ADD = ('add',)
GIT_COMMIT = ('commit', '-v', '--untracked-files=no')
GIT_STATUS_PORCELAIN = ('status', '--porcelain')
GIT_CLONE = (GIT_PROGRAM, 'clone')
GIT_LIST_BRANCHES = ('branch', '-l')
GIT_LIST_TAGS = ('tag', '-l')
GIT_GET_BRANCH = ('branch',)
GIT_STASH = ('stash',)
GIT_UNSTASH = ('stash', 'pop')
GIT_REBASE_I = ('rebase', '-i')
GIT_PUSH = ('push',)
GIT_REVERT_ALL = ('reset', '--hard')
GIT_REVERT_1 = ('reset', 'HEAD')
GIT_REVERT_2 = ('checkout', '--')
GIT_DIFF = ('diff',)
GIT_LIST_FILES = ('ls-files',)

SHELL_REGEX = re.compile("^[a-zA-Z0-9_-]*$")

def format_shell_arg(arg):
    if sys.hexversion >= 0x03030000:
        return shlex.quote(arg)
    elif SHELL_REGEX.match(arg): # No quoting necessary
        return arg
    else:                        # Safe quoting
        return "'%s'" % arg.replace("'", "'\"'\"'")

def format_shell_args(args):
    return ' '.join(format_shell_arg(arg) for arg in args)

def filesystem_sync():
    exitcode = subprocess.call('sync')
    if exitcode:
        print("sync failed: exit code %s" % exitcode)
        sys.exit(exitcode)

ANSI_COLORS = re.escape("\x1B[") + "[0-9;]*[a-zA-Z]"
ANSI_COLORS = "(?:%s)*" % ANSI_COLORS
ANSI_COLORS = re.compile("^(%s)(.*?)(%s)$" % (ANSI_COLORS, ANSI_COLORS))

if not hasattr(os.path, 'relpath'):
    # Backport from Python 2.7 for Python < 2.6
    def relpath(path, start=os.path.curdir):
        """Return a relative version of a path"""

        if not path:
            raise ValueError("no path specified")

        start_list = [x for x in os.path.abspath(start).split(os.path.sep) if x]
        path_list = [x for x in os.path.abspath(path).split(os.path.sep) if x]

        # Work out how much of the filepath is shared by start and path.
        i = len(os.path.commonprefix([start_list, path_list]))

        rel_list = [os.path.pardir] * (len(start_list)-i) + path_list[i:]
        if not rel_list:
            return os.path.curdir
        return os.path.join(*rel_list)
    os.path.relpath = relpath

def split_ansi_colors(text):
    r"""
    >>> split_ansi_colors('\x1b[35m\x1b[Kprofile/packages\x1b[m\x1b[K\x1b[36m\x1b[K')
    ('\x1b[35m\x1b[K', 'profile/packages', '\x1b[m\x1b[K\x1b[36m\x1b[K')
    """
    m = ANSI_COLORS.match(text)
    if not m:
        raise ValueError("Failed to find colors in %r" % text)
    return m.groups()

def ask_confirmation(prompt):
    try:
        answer = raw_input(prompt)
    except EOFError:
        print("no")
        answer = ''
    else:
        answer = answer.strip().lower()
    return answer

class Application:
    def __init__(self):
        self._exitcode = 0
        self.verbose = False
        # Directory at program startup
        self.start_directory = os.path.realpath(os.getcwd())
        # Root of all repositories
        self.root = self.start_directory
        self.reset()

    def main(self):
        if len(sys.argv) < 2:
            usage()
        if sys.argv[1] in ('-v', '--verbose'):
            self.verbose = True
            if len(sys.argv) < 3:
                usage()
            self.command = sys.argv[2]
            self.args = tuple(sys.argv[3:])
        else:
            self.command = sys.argv[1]
            self.args = tuple(sys.argv[2:])

        try:
            self.process_command()
        except KeyboardInterrupt:
            print("")
            print("Interrupted!")
            self.set_exitcode(1)
        sys.exit(self._exitcode)

    def process_command(self):
        commands = {
            "clone": self.clone,
            "pull": self.pull,
            "status": self.status,
            "st": self.status,
            "out": self.out,
            "scan": self.scanner,
            "clean":  self.cleanup,
            "distclean":  self.distclean,
            "remove_untracked":  self.remove_untracked,
            "stash": self.stash,
            "unstash": self.unstash,
            "push": self.push,
            "diff": self.diff,
            "add": self.add,
            "commit": self.commit,
            "ci": self.commit,
            "histedit": self.histedit,
            "tag_contains": self.tag_contains,
            "revert": self.revert,
            "info": self.info,
            "branches": self.list_branches,
            "branch": self.branch,
            "tags": self.list_tags,
            "grep": self.grep,
            "files": self.list_files,
            "selftest": self.selftest,
        }
        try:
            func = commands[self.command]
        except KeyError:
            usage()
        else:
            func()

    def noargs(self):
        if not self.args:
            return
        print("The %s command does not take any argument" % self.command)
        sys.exit(1)

    def reset(self):
        self.has_config = None
        self.repositories = []

    def clone(self):
        self.noargs()
        self.setup(need_config=True)
        for repository in self.repositories:
            if not repository.exists():
                repository.clone()
            else:
                print("Skip %s: already exists" % repository.name)

    def iter_existing_repositories(self):
        for repository in self.repositories:
            if not repository.exists():
                print("WARNING: %s is missing" % repository.name)
                continue
            yield repository

    def list_branches(self):
        self.noargs()
        self.setup()
        for repository in self.iter_existing_repositories():
            repository.list_branches()

    def branch(self):
        self.noargs()
        self.setup()
        for repository in self.iter_existing_repositories():
            repository.branch()

    def list_tags(self):
        self.noargs()
        self.setup()
        for repository in self.iter_existing_repositories():
            repository.list_tags()

    def only_one_local_scm(self):
        count = 0
        for repository in self.repositories:
            if not repository.exists():
                continue
            count += 1
            if count > 1:
                return False
        return (count == 1)

    def grep(self):
        if not len(self.args):
            print("grep requires at least one argument")
            sys.exit(1)
        self.setup()
        display_if_empty = self.verbose or self.only_one_local_scm()
        found = False
        for repository in self.iter_existing_repositories():
            found |= repository.grep(self.args, display_if_empty=display_if_empty)
        if not found:
            self.set_exitcode(1)

    def list_files(self):
        self.noargs()
        self.setup()
        found = False
        for repository in self.iter_existing_repositories():
            found |= repository.list_files()
        if not found:
            self.set_exitcode(1)

    def selftest(self):
        import doctest
        failures, ntests = doctest.testmod()
        if failures:
            self.set_exitcode(1)
        else:
            print("%s tests are OK." % ntests)

    def info(self):
        self.noargs()
        self.setup()
        existing = 0
        for repository in self.iter_existing_repositories():
            repository.info()
            existing += 1
        if self.has_config:
            text = "Total: %s repositories" % len(self.repositories)
            missing = len(self.repositories) - existing
            if missing:
                text += " (%s missing)" % missing
            print(text)

    def pull(self):
        self.noargs()
        self.setup()
        errors = []
        for repository in self.repositories:
            try:
                if repository.exists():
                    repository.pull()
                else:
                    repository.clone()
            except SystemExit as exc:
                self.system_exit(exc)
                errors.append(repository)
        for repository in errors:
            print("Failed to pull: %s" % repository)

    def status(self):
        if len(self.args) == 1:
            self.setup_local(use_args=True)
            for repository in self.iter_existing_repositories():
                repository.status(self.args)
        elif len(self.args) == 0:
            self.setup()
            for repository in self.iter_existing_repositories():
                repository.status(tuple())
        else:
            print("status takes no argument or one argument, not %s" % len(self.args))
            sys.exit(1)

    def out(self):
        self.noargs()
        self.setup()
        display_if_empty = self.verbose or self.only_one_local_scm()
        for repository in self.iter_existing_repositories():
            print("Check repository %s" % repository)
            repository.out(display_if_empty)

    def processing(self):
        if self.has_config:
            print("Processing %s repositories" % len(self.repositories))
        else:
            repository = self.repositories[0]
            print("Processing %s" % repository)

    def cleanup(self):
        self.noargs()
        self.setup()
        self.processing()
        for repository in self.iter_existing_repositories():
            repository.clean()

    def distclean(self):
        if self.args == ('--remove',):
            remove = True
        elif self.args:
            print("Unknown command line options")
            sys.exit(1)
        else:
            remove = False

        self.setup()
        self.processing()
        for repository in self.iter_existing_repositories():
            repository.distclean(remove)

    def remove_untracked(self):
        self.noargs()
        self.setup()
        self.processing()
        for repository in self.iter_existing_repositories():
            repository.remove_untracked()

    def _parse_config(self, line, filter_path):
        try:
            destdir, _, data = line.partition(':')
            destdir = destdir.rstrip()
            data = data.lstrip()
            scm, _, url = data.partition('=')
        except Exception as err:
            print("Unable to parse line %r: %s" % (line, err))
            sys.exit(1)
        if filter_path:
            if not destdir.startswith(filter_path):
                return
        klass = SCM_CLASSES[scm]
        repository = klass(self, destdir, url=url)
        self.repositories.append(repository)

    def read_config(self, filename, filter_path=None):
        if filter_path and not filter_path.endswith(os.sep):
            filter_path += os.sep
        self.has_config = True
        with open(filename) as fp:
            for line in fp:
                # strip comments
                line = line.split('#', 1)[0]
                # strip trailing spaces and newline characters
                line = line.rstrip()
                if not line:
                    # ignore empty lines
                    continue
                self._parse_config(line, filter_path)
        if not self.repositories:
            print("No repository configured: nothing to do, exit")
            sys.exit(0)

    def search_scm(self, search_config=False, start_directory=None):
        seen = set()
        if start_directory:
            dirpath = start_directory
        else:
            dirpath = self.start_directory
        while True:
            if dirpath == '/':
                return False
            if dirpath in seen:
                print("Recusion in parent directories, exit")
                sys.exit(0)
            seen.add(dirpath)
            self.root = dirpath

            config = os.path.join(dirpath, CONFIG_FILENAME)
            if search_config and os.path.exists(config):
                filter_path = os.path.relpath(self.start_directory, dirpath)
                self.read_config(config, filter_path)
                return True
            repository = self.parse_local_scm(dirpath)
            if repository is not None:
                self.repositories.append(repository)
                return True

            dirpath = os.path.realpath(os.path.join(dirpath, '..'))
        return False

    def parse_local_scm(self, directory):
        for scm in SCM_CLASSES.values():
            repository = scm.parse(self, directory)
            if repository is not None:
                return repository
        return None

    def setup_local(self, use_args=False):
        self.reset()
        if use_args:
            directory = os.path.commonprefix([arg for arg in self.args
                                              if not arg.startswith('-')])
        else:
            directory = None
        if directory:
            directory = os.path.join(self.start_directory, directory)
        found = self.search_scm(start_directory=directory)
        if not found:
            print("Unable to find a SCM in %s" % self.start_directory)
            sys.exit(1)

    def setup(self, need_config=False):
        self.reset()
        if os.path.exists(CONFIG_FILENAME):
            self.read_config(CONFIG_FILENAME)
            return
        found = self.search_scm(search_config=True)
        if not found:
            if need_config:
                print("Unable to find %s" % CONFIG_FILENAME)
                sys.exit(1)
            print("Unable to find %s or to locate a SCM in %s"
                   % (CONFIG_FILENAME, self.start_directory))
            sys.exit(1)

    def stash(self):
        self.noargs()
        self.setup_local()
        repository = self.repositories[0]
        local_changes = repository.stash()
        if not local_changes:
            self.set_exitcode(1)

    def unstash(self):
        self.noargs()
        self.setup_local()
        repository = self.repositories[0]
        restored = repository.unstash()
        if not restored:
            self.set_exitcode(1)

    def push(self):
        self.noargs()
        self.setup_local()
        repository = self.repositories[0]
        repository.push()

    def diff(self):
        if self.args:
            self.setup_local(use_args=True)
            repository = self.repositories[0]
            repository.diff(self.args)
        else:
            self.setup()
            for repository in self.iter_existing_repositories():
                repository.diff(self.args)

    def add(self):
        self.setup_local()
        repository = self.repositories[0]
        repository.add(self.args)

    def commit(self):
        self.setup_local()
        repository = self.repositories[0]
        repository.commit(self.args)

    def histedit(self):
        self.setup_local()
        if len(self.args) != 1:
            print("histedit requires one argument: the revision, not %s" % len(self.args))
            sys.exit(1)
        revision = self.args[0]
        repository = self.repositories[0]
        repository.histedit(revision)

    def revert(self):
        if self.args:
            self.setup_local(use_args=True)
            repository = self.repositories[0]
            repository.command_revert(self.args, verbose=True)
        else:
            self.setup()
            modified = False
            for repository in self.iter_existing_repositories():
                modified |= repository.command_revert(self.args, verbose=False)
            if not modified:
                print("All repositories are clean.")

    def tag_contains(self):
        self.setup_local()
        if len(self.args) != 1:
            print("tag_contains requires one argument: the revision, not %s"
                  % len(self.args))
            sys.exit(1)
        revision = self.args[0]
        repository = self.repositories[0]
        repository.tag_contains(revision)

    def set_exitcode(self, exitcode):
        if self._exitcode is None:
            self._exitcode = exitcode
        elif exitcode != 0:
            self._exitcode = exitcode

    def system_exit(self, exc):
        exitcode = exc.code
        if not isinstance(exitcode, int):
            exitcode = 1
        self.set_exitcode(exitcode)

    def _scanner(self, directory):
        ignored = 0
        try:
            names = os.listdir(directory)
        except OSError as err:
            print(("WARNING: Failed to browse %s directory: %s"
                   % (directory, err)), file=sys.stderr)
            return ignored
        for name in names:
            fullname = os.path.join(directory, name)
            if not os.path.isdir(fullname):
                continue
            repository = self.parse_local_scm(fullname)
            if repository is not None:
                if repository.url is not None:
                    self.repositories.append(repository)
                    print("-> %s" % repository, file=sys.stderr)
                else:
                    print("IGNORE: %s (unable to get the parent)" % repository,
                          file=sys.stderr)
                    ignored += 1
                continue
            else:
                ignored += self._scanner(fullname)
        return ignored

    def scanner(self):
        self.noargs()
        self.reset()
        print("Search HG and GIT projects in %s..." % self.root,
              file=sys.stderr)
        ignored = self._scanner(self.root)
        print(file=sys.stderr)
        if not self.repositories:
            print("Did not find any repository in %s" % self.start_directory,
                  file=sys.stderr)
            self.set_exitcode(1)
            return

        # FIXME: fix order for dependencies
        print('# Format: "directory: scm=url"')
        self.repositories.sort(key=lambda repository: repository.name)
        for repository in self.repositories:
            print("%s: %s=%s"
                   % (repository.name, repository.SCM, repository.url))
        print(file=sys.stderr)
        print("Found %s repositories" % len(self.repositories), file=sys.stderr)
        if ignored:
            print("WARNING: %s repository/ies has been ignored" % ignored,
                  file=sys.stderr)


class Repository:
    SCM = None

    def __init__(self, application, directory, url=None):
        self.application = application
        self._url = url
        # directory is relative to application.root
        self.root = os.path.realpath(os.path.join(self.application.root, directory))
        if self.root != self.application.start_directory:
            self.relpath = os.path.relpath(self.root, self.application.start_directory)
        else:
            self.relpath = ''
        if self.application.start_directory.startswith(self.root):
            name = os.path.basename(self.root)
            if self.relpath:
                name = "%s (%s)" % (name, self.relpath)
        else:
            name = self.relpath
        self.name = name

    def get_url(self):
        if self._url is None:
            url = self._get_url()
            if url is None:
                url = ''
            self._url = url
        return self._url

    def relative_filenames(self, filenames):
        return tuple(os.path.relpath(filename, self.root) for filename in filenames)

    def ask_confirmation(self, prompt):
        while True:
            try:
                answer = ask_confirmation(prompt + " [y/N/d/?]:")
            except KeyboardInterrupt:
                print("no")
                answer = ''
            if (not answer) or answer in ('n', 'no', 'q', 'quit', 'exit'):
                sys.exit(1)
            elif answer in ('y', 'yes'):
                return "revert"
            elif answer in ('d', 'diff'):
                self.diff(tuple())
                print("")
                continue
            else:
                if answer not in ('?', 'help'):
                    print('Sorry, I don\'t understand "%s"' % answer)
                    print("")
                print("no, n, quit, q or exit (default): do nothing, exit")
                print("yes or y: revert changes")
                print("diff or d: show differences")
                print("?: show this help")
                print("")

    def print_text(self, text):
        text = "%s: %s" % (self.name, text)
        print(text)
        print("=" * len(text))
        print("")

    def info_text(self, text):
        print("+ " + text)

    def write_output(self, cmd, output):
        self.info_text(format_shell_args(cmd))
        output = output.rstrip()
        print(output)
        if output:
            print("")

    def get_status_output(self, cmd, stderr=None, **kw):
        if stderr == 'null':
            null = open(os.devnull, 'wb')
            stderr = null
        else:
            null = None
            stderr = subprocess.STDOUT
        if 'cwd' in kw:
            cwd = kw.pop('cwd')
        else:
            cwd = self.root
        env = os.environ.copy()
        for name in ('LC_ALL', 'LC_CTYPE', 'LANG'):
            if name in env:
                del env[name]
        try:
            sys.stdout.flush()
            sys.stderr.flush()
            process = subprocess.Popen(cmd,
                                       stdout=subprocess.PIPE,
                                       stderr=stderr,
                                       cwd=cwd,
                                       env=env,
                                       universal_newlines=True)
        finally:
            if null:
                null.close()
        stdout, stderr = process.communicate()
        exitcode = process.wait()
        return exitcode, stdout

    def get_output(self, cmd, **kw):
        exitcode, stdout = self.get_status_output(cmd, **kw)
        if exitcode:
            self.write_output(cmd, stdout)
            sys.exit(exitcode)
        return stdout

    def run(self, cmd, **kw):
        verbose = kw.pop('verbose', None)
        quiet = kw.pop('quiet', False)
        stdin = kw.pop('stdin', None)
        stdout = kw.pop('stdout', None)
        suffix = kw.pop('suffix', '')
        env = kw.pop('env', None)
        if 'cwd' in kw:
            cwd = kw.pop('cwd')
        else:
            cwd = self.root
        set_exitcode = kw.pop('set_exitcode', False)
        ignore_exitcode = kw.pop('ignore_exitcode', False)
        if kw:
            raise ValueError("Unknown keywords: %s" % kw.keys())

        if verbose is None:
            verbose = not quiet
        else:
            if verbose and quiet:
                raise ValueError("verbose and quiet cannot be used together")
        if set_exitcode and ignore_exitcode:
            raise ValueError("set_exitcode and ignore_exitcode cannot be used together")

        title = format_shell_args(cmd) + suffix
        popen_args = {
            'stdin': stdin,
            'stdout': stdout,
            'cwd': cwd,
            'env': env,
        }
        if verbose:
            self.print_text(title)
        elif not quiet:
            self.info_text(title)
        sys.stdout.flush()
        sys.stderr.flush()
        exitcode = subprocess.call(cmd, **popen_args)
        if set_exitcode:
            self.application.set_exitcode(exitcode)
        elif not ignore_exitcode:
            if exitcode:
                sys.exit(exitcode)
        if verbose:
            print("")
        return exitcode

    @contextlib.contextmanager
    def revert_local_changes(self):
        """
        Context manager to stash at enter and unstash at exit.
        """
        local_changed = self.stash(verbose=False)
        try:
            yield
        finally:
            if local_changed:
                self.unstash(verbose=False)

    def info(self):
        self.print_text("Informations")
        self._info()
        print("scm = %s" % self.SCM)
        print("has local changes? %s" % self.has_local_changes())
        print("root = %s" % self.root)
        url = self.get_url()
        if url is not None:
            print("url = %s" % url)
        print("")

    def exists(self):
        return os.path.exists(self.root)

    def clean(self):
        for dirpath, dirnames, filenames in os.walk(self.root):
            for name in filenames:
                if name.endswith(CLEAN_SUFFIXES):
                    fullname = os.path.join(dirpath, name)
                    print("Remove file: %s" % os.path.relpath(fullname, self.application.start_directory))
                    os.unlink(fullname)
            if '__pycache__' in dirnames:
                fullpath = os.path.join(dirpath, '__pycache__')
                print("Remove directory: %s" % os.path.relpath(fullpath, self.application.start_directory))
                rmtree(fullpath)
        self._clean()

    def distclean(self, remove):
        self.clean()

        tracked_files = self._get_existing_files()
        tracked_files = [os.path.join(self.root, filename) for filename in tracked_files]
        dirs = set()
        for filename in tracked_files:
            dirname = filename
            while True:
                dirname = os.path.dirname(dirname)
                if dirname == self.root:
                    break
                dirs.add(dirname)
        tracked_files = set(tracked_files) | dirs
        tracked_files.add(os.path.join(self.root, '.git'))
        tracked_files.add(os.path.join(self.root, '.hg'))

        noop = True
        for dirpath, dirnames, filenames in os.walk(self.root):
            for exclude_dir in DISTCLEAN_EXCLUDED_DIRS:
                try:
                    dirnames.remove(exclude_dir)
                except ValueError:
                    pass

            for name in filenames:
                fullname = os.path.join(dirpath, name)
                if fullname not in tracked_files:
                    print("Remove file %s" % fullname)
                    if remove:
                        os.unlink(fullname)
                    noop = False
            for name in dirnames:
                fullname = os.path.join(dirpath, name)
                if fullname not in tracked_files:
                    print("Remove directory %s" % fullname)
                    if remove:
                        shutil.rmtree(fullname)
                    noop = False
        if not remove and not noop:
            print("")
            print("Now pass the --remove option to really remove files")

    def _clean(self):
        pass

    def __str__(self):
        return "%s (%s)" % (self.name, self.SCM)

    def __repr__(self):
        return "%s<%s>" % (self.__class__.__name__, str(self))

    def remove_untracked(self):
        remove_all = False
        for filename in self.get_untracked_files():
            relname = os.path.relpath(filename, self.application.start_directory)
            if remove_all:
                print("Remove %s" % relname)
                os.unlink(filename)
                continue
            prompt = "Remove untrack file: %s (y/a/N)? " % relname
            try:
                answer = ask_confirmation(prompt)
            except KeyboardInterrupt:
                print("no")
                sys.exit(0)
            if answer in ('a', 'all'):
                remove_all = True
            elif answer not in ('y', 'yes'):
                continue
            os.unlink(filename)

    def _info(self):
        raise NotImplementedError()

    @classmethod
    def parse(cls, application, directory):
        raise NotImplementedError()

    def stash(self, verbose=True):
        """
        Return True if there was local changes and a stash file has been
        created.
        """
        raise NotImplementedError()

    def push(self):
        raise NotImplementedError()

    def add(self, args):
        raise NotImplementedError()

    def diff(self, args):
        raise NotImplementedError()

    def commit(self, args):
        raise NotImplementedError()

    def histedit(self, revision):
        raise NotImplementedError()

    def tag_contains(self, revision):
        raise NotImplementedError()

    def command_revert(self, args, verbose=True):
        if not args:
            filenames = self.get_modified_files()
            if (not filenames) and (not self.has_local_changes()):
                if verbose:
                    print("No local changes, exit")
                return False

            if filenames:
                nfiles = len(filenames)
                if 5 < nfiles:
                    filenames[5] = '...'
                    del filenames[6:]
                files = ", ".join(filenames)
                prompt = "DO YOU REALLY WANT TO REVERT ALL %s LOCAL CHANGES (%s files): %s" % (self.name, nfiles, files)
            else:
                prompt = "DO YOU REALLY WANT TO REVERT ALL %s LOCAL CHANGES" % self.name
        else:
            prompt = "Do you really want to revert %s" % ', '.join(args)
        self.ask_confirmation(prompt)
        self.revert(args)
        return True

    def _process_grep_output(self, stdout):
        if not self.relpath:
            return stdout
        lines = []
        for line in stdout.splitlines():
            parts = line.split(':', 1)
            if len(parts) == 2:
                filename = parts[0]
                prefix, filename, suffix = split_ansi_colors(filename)
                filename = os.path.join(self.relpath, filename)
                filename = os.path.relpath(filename, self.application.start_directory)
                line = ''.join((prefix, filename, suffix, ':', parts[1]))
            lines.append(line)
        return '\n'.join(lines)

    def grep(self, args, display_if_empty=True):
        """
        Return True if the pattern was found, False otherwise.
        """
        files, prefix = self.get_existing_files()
        if not files:
            print("WARNING: The repository doesn't track any file in the current directory.")
            return False

        cmd = GREP + args + ('--',) + tuple(files)
        if prefix is not None:
            exitcode, output = self.get_status_output(cmd, cwd=None)
        else:
            exitcode, output = self.get_status_output(cmd)
        found = (exitcode == 0)
        if (not output) and (not display_if_empty):
            return found

        output = output.strip()
        if prefix is None:
            output = self._process_grep_output(output)

        self.print_text("Grep %s -- <%s filenames>" % (format_shell_args(args), len(files)))
        output = output.rstrip()
        print(output)
        if output:
            print("")
        return found

    def list_files(self):
        """
        Return True if at least one file matchs the pattern, False otherwise.
        """
        files, prefix = self.get_existing_files()
        if not files:
            print("WARNING: The repository doesn't track any file in the current directory.")
            return False
        for file in files:
            print(file)
        return True

    #--- abstract methods ---

    def revert(self, args):
        raise NotImplementedError()

    def has_local_changes(self):
        """
        Return True if the repository has local changes (not commited yet),
        False otherwise.
        """
        raise NotImplementedError()

    def get_modified_files(self):
        """
        Return the list of filenames modified locally.
        """
        raise NotImplementedError()

    def get_untracked_files(self):
        """
        Return the list of names of untracked files.
        """
        raise NotImplementedError()

    def get_branch(self):
        raise NotImplementedError()

    def branch(self):
        branch = self.get_branch()
        print("%s: %s" % (self.name, branch))

    def list_branches(self):
        raise NotImplementedError()

    def list_tags(self):
        raise NotImplementedError()

    def unstash(self, verbose=True):
        """
        Return True if changes were restored, False if there was no
        changes.
        """
        raise NotImplementedError()

    def status(self, args):
        raise NotImplementedError()

    def out(self, display_if_empty=True):
        raise NotImplementedError()

    def clone(self):
        raise NotImplementedError()

    def pull(self):
        raise NotImplementedError()

    def get_existing_files(self):
        """
        Return (files, prefix) where files is the list of all files that exist
        on disk (e.g. ignore removed files).
        """
        files = self._get_existing_files()
        if self.application.start_directory != self.root \
        and not self.root.startswith(self.application.start_directory):
            prefix = os.path.relpath(self.application.start_directory, self.root)
            if not prefix.endswith(os.sep):
                prefix += os.sep
            prefix_len = len(prefix)
            files = [
                filename[prefix_len:]
                for filename in files
                if filename.startswith(prefix)]
        else:
            prefix = None
        return files, prefix

    def _get_existing_files(self):
        raise NotImplementedError()

class RepositoryHG(Repository):
    SCM = 'hg'

    def __init__(self, application, directory, url=None):
        Repository.__init__(self, application, directory, url)
        self.stash_file = os.path.join(self.root, '.hg', STASH_FILENAME)

    @classmethod
    def parse(cls, application, directory):
        hgdir = os.path.join(directory, '.hg')
        if not os.path.isdir(hgdir):
            return None
        return RepositoryHG(application, directory)

    def _get_url(self):
        hgrc = os.path.join(hgdir, 'hgrc')
        parser = RawConfigParser()
        try:
            parser.read(hgrc)
            return parser.get('paths', 'default')
        except NoSectionError:
            return None
        except Exception as err:
            print("WARNING: Fail to parse %s: %s" % (hgrc, err),
                  file=sys.stderr)
            return None

    def process_status(self, output):
        lines = output.splitlines()
        output = []
        use_ignore = (not self.application.verbose)
        for line in lines:
            if use_ignore and line.startswith(b'? '):
                filename = line[2:]
                if filename.endswith(STATUS_IGNORE_EXT):
                    continue
                if filename in STATUS_IGNORE_FILES:
                    continue
            if 3 <= len(line) \
            and line.startswith((b"? ", b"M ", b"A ")):
                filename = os.path.join(self.root, line[2:])
                filename = os.path.relpath(filename, self.application.start_directory)
                line = line[:2] + filename
            output.append(line)
        return '\n'.join(output)

    def list_branches(self):
        self.run(HG_LIST_BRANCHES)

    def get_branch(self):
        output = self.get_output(HG_BRANCH)
        return output.rstrip()

    def list_tags(self):
        self.run(HG_LIST_TAGS)

    def has_local_changes(self):
        stdout = self.get_output((HG_PROGRAM, 'id', '--num'))
        revision_number = stdout.strip()
        return ("+" in revision_number)

    def get_modified_files(self):
        status = self.get_output(HG_STATUS)
        filenames = []
        for line in status.splitlines():
            if line.startswith("?"):
                continue
            filenames.append(line[2:])
        return filenames

    def get_untracked_files(self):
        status = self.get_output(HG_STATUS)
        filenames = []
        for line in status.splitlines():
            if line.startswith("?"):
                filename = os.path.join(self.root, line[2:])
                filenames.append(filename)
        return filenames

    def _info(self):
        stdout = self.get_output((HG_PROGRAM, 'id', '--num', '--branch'), stderr="null")
        parts = stdout.strip().split()
        revision, branch = parts
        print("revision: %s" % revision)
        print("branch: %s" % branch)

    def _clean(self):
        strip_backup = os.path.join(self.root, '.hg', 'strip-backup')
        if os.path.exists(strip_backup):
            print("Remove directory %s" % os.path.relpath(strip_backup, self.application.start_directory))
            rmtree(strip_backup)

    def stash(self, verbose=True):
        dest = self.stash_file
        if os.path.exists(dest):
            print("%s does already exist!" % os.path.join(self.root, dest))
            sys.exit(1)
        fp = open(dest, "wb")
        try:
            env = os.environ.copy()
            # importing the readline module writes b'\033[?1034h' to stdout
            # if the TERM envrionment variable is "xterm"
            env['TERM'] = 'dummy'
            with fp:
                self.run(HG_DIFF,
                         stdout=fp,
                         verbose=False,
                         suffix=' > %s # stash' % dest,
                         env=env)
        except:
            os.unlink(dest)
            raise
        filesize = os.path.getsize(dest)
        if not filesize:
            if verbose:
                print("No local change")
            os.unlink(dest)
            return False
        filesystem_sync()
        self.run(HG_REVERT_ALL, verbose=False)
        return True

    def unstash(self, verbose=True):
        dest = self.stash_file
        if not os.path.exists(dest):
            print("No stash file has been found: %s" % os.path.join(self.root, dest))
            return False
        with open(dest, "rb") as fp:
            self.run((PATCH_PROGRAM, '-p1'), stdin=fp, verbose=False, suffix=' < %s # unstash' % dest)
        filesystem_sync()
        os.unlink(dest)
        if verbose:
            print("Local changes restored.")
        return True

    def status(self, args):
        display_if_empty = self.application.verbose
        if args:
            stdout = self.get_output(HG_STATUS + args, cwd=None)
        else:
            stdout = self.get_output(HG_STATUS)
        stdout = self.process_status(stdout)
        if (not stdout) and (not display_if_empty):
            return
        self.print_text("Status")
        self.write_output(HG_STATUS, stdout)

    def out(self, display_if_empty=True):
        if display_if_empty:
            self.run(HG_OUT, ignore_exitcode=True)
        else:
            exitcode, stdout = self.get_status_output(HG_OUT)
            if exitcode not in (0, 1):
                self.application.set_exitcode(exitcode)
                return
            if exitcode == 1:
                # no change found
                return
            self.print_text("Output commits")
            self.write_output(HG_OUT, stdout)

    def is_file_url(self, url):
        return (not url.startswith(("ssh://", "http://", "https://")))

    def clone(self):
        parent = os.path.dirname(self.root)
        url = self.url
        if url is None:
            print("Don't know the URL of the repository %s" % self)
            sys.exit(1)
        if self.is_file_url(url) and not os.path.isabs(url):
            url = os.path.realpath(os.path.join(self.root, url))
        self.run(HG_CLONE + (url, self.root), cwd=parent)

    def _pull(self):
        pull = HG_PULL
        if self.application.verbose:
            pull += ('--verbose',)
        self.run(pull, suffix=" # %s" % self.url, verbose=False)

    def pull(self):
        self.print_text('Pull')
        with self.revert_local_changes():
            self._pull()
            self.run(HG_UPDATE, verbose=False)
        print("")

    def add(self, args):
        self.run(HG_ADD + args)

    def diff(self, args):
        if not args:
            args = (self.relpath,)
        cmd = HG_DIFF + args
        self.run(cmd, cwd=None, quiet=not self.application.verbose)

    def commit(self, args):
        self.run(HG_COMMIT + args, verbose=False, cwd=None)

    def histedit(self, revision):
        self.print_text("Histedit %s" % revision)
        with self.revert_local_changes():
            self.run(HG_HISTEDIT + (revision,),
                     verbose=False, set_exitcode=True)

    def tag_contains(self, revision):
        revset = "reverse(descendants(%s)) and tag()" % revision
        args = (HG_PROGRAM, 'log',
                    '-r', revset,
                    '--template', r'{tags}\t{rev}:{node|short}\n')
        self.run(args)

    def revert(self, args):
        if args:
            self.run(HG_REVERT + args)
        else:
            self.run(HG_REVERT + ('--all',))
            self.run(HG_UPDATE_CLEAN)

    def push(self):
        self.print_text("Push")
        with self.revert_local_changes():
            self._pull()
        self.run(HG_PUSH, verbose=False)
        print("")

    def _get_existing_files(self):
        cmd = HG_STATUS + ('--no-status', '--clean', '--modified', '--added')
        output = self.get_output(cmd)
        output = output.strip()
        return output.splitlines()

class RepositoryGIT(Repository):
    SCM = 'git'

    def __init__(self, application, directory, url=None, gitdir=None):
        Repository.__init__(self, application, directory, url)
        if gitdir is None:
            gitdir = os.path.join(directory, '.git')
        self.gitdir = gitdir

    def _get_url(self):
        gitconfig = os.path.join(self.gitdir, 'config')
        if not os.path.exists(gitconfig):
            return None

        with open(gitconfig) as fp:
            lines = [line.strip() for line in fp]

        try:
            content = StringIO('\n'.join(lines))
            parser = RawConfigParser()
            parser.readfp(content)
            return parser.get('remote "origin"', 'url')
        except Exception as err:
            print("WARNING: Fail to parse %s: %s" % (gitconfig, err),
                  file=sys.stderr)
            return None

    @classmethod
    def parse(cls, application, directory):
        gitdir = os.path.join(directory, '.git')
        if os.path.exists(gitdir) and not os.path.isdir(gitdir):
            with open(gitdir) as fp:
                line = fp.readline().rstrip()

            if line.startswith('gitdir: '):
                gitdir = line[8:]

        filename = os.path.join(gitdir, 'index')
        if not os.path.exists(filename):
            return None

        return RepositoryGIT(application, directory, gitdir=gitdir)

    def list_branches(self):
        self.run(self._gitcmd(GIT_LIST_BRANCHES))

    def list_tags(self):
        self.run(self._gitcmd(GIT_LIST_TAGS))

    def has_local_changes(self):
        exitcode, stdout = self.get_status_output(self._gitcmd(GIT_STATUS_PORCELAIN))
        for line in stdout.splitlines():
            if line.startswith("?"):
                continue
            return True
        return False

    def get_branch(self):
        stdout = self.get_output(self._gitcmd(GIT_GET_BRANCH))
        branch = None
        for line in stdout.splitlines():
            if line.startswith('* '):
                branch = line[2:]
                break
        if not branch:
            raise Exception("Unable to find the branch in %r" % stdout)
        return branch

    def _info(self):
        branch = self.get_branch()
        print("branch = %s" % branch)

    def add(self, args):
        self.run(self._gitcmd(GIT_ADD + args), verbose=False)

    def out(self, display_if_empty=True):
        git_out = self._gitcmd(('log',
                                '@{upstream}..',
                                "--pretty=format:%Cred%h%Creset %s",
                                "--color=%s" % COLORS))

        if display_if_empty:
            self.print_text("Output commits")
            self.run(git_out, verbose=False, set_exitcode=True)
        else:
            exitcode, stdout = self.get_status_output(git_out)
            self.application.set_exitcode(exitcode)
            if not stdout:
                return
            self.print_text("Output commits")
            self.write_output(git_out, stdout)

    def commit(self, args):
        self.run(self._gitcmd(GIT_COMMIT + args), quiet=True, set_exitcode=True)

    def status(self, args):
        if args:
            args = self.relative_filenames(args)
            args = self._gitcmd(GIT_STATUS_PORCELAIN + args)
            exitcode, stdout = self.get_status_output(args)
        else:
            args = self._gitcmd(GIT_STATUS_PORCELAIN)
            exitcode, stdout = self.get_status_output(args)
        if not self.application.verbose:
            # filter files
            lines = []
            for line in stdout.splitlines():
                pos = 3
                filename = line[pos:]
                if filename.endswith(STATUS_IGNORE_EXT):
                    continue
                if filename in STATUS_IGNORE_FILES:
                    continue
                if self.relpath:
                    filename = os.path.join(self.relpath, filename)
                    line = line[:pos] + filename
                lines.append(line)
            if not lines:
                return
            stdout = '\n'.join(lines)
        else:
            if not stdout:
                return
        self.print_text("Status")
        self.write_output(args, stdout)

    def clone(self):
        self.run(GIT_CLONE + (self.url, self.root), cwd=None)

    def _pull(self):
        pull = self._gitcmd(GIT_PULL)
        if self.application.verbose:
            pull += ('--verbose',)
        self.run(pull, suffix=" # %s" % self.url, verbose=False)

    def pull(self):
        self.print_text('Pull')
        with self.revert_local_changes():
            self._pull()
        print("")

    def stash(self, verbose=True):
        """
        Return True if there was local changes and a stash file has been
        created.
        """
        text = format_shell_args(self._gitcmd(GIT_STASH))
        if verbose:
            self.print_text(text)
        else:
            self.info_text(text)
        stdout = self.get_output(self._gitcmd(GIT_STASH))
        if verbose:
            self.write_output(self._gitcmd(GIT_STASH), stdout)
        return ("No local changes to save" not in stdout)

    def unstash(self, verbose=True):
        """
        Return True if there was local changes and a stash file has been
        created.
        """
        exitcode = self.run(self._gitcmd(GIT_UNSTASH), ignore_exitcode=True)
        if exitcode:
            return False
        else:
            return True

    def diff(self, args):
        args = self.relative_filenames(args)
        cmd = self._gitcmd(GIT_DIFF) + args
        self.run(cmd, quiet=not self.application.verbose)

    def histedit(self, revision):
        self.print_text("Histedit %s" % revision)
        with self.revert_local_changes():
            self.run(self._gitcmd(GIT_REBASE_I + (revision,)),
                     verbose=False, set_exitcode=True)

    def tag_contains(self, revision):
        args = self._gitcmd(('tag', '--contains', revision))
        self.run(args)

    def push(self):
        self.print_text("Push")
        with self.revert_local_changes():
            self._pull()
        self.run(self._gitcmd(GIT_PUSH), verbose=False)
        print("")

    def get_modified_files(self):
        filenames = []
        exitcode, stdout = self.get_status_output(self._gitcmd(GIT_STATUS_PORCELAIN))
        if 'working directory clean' in stdout:
            return filenames
        for line in stdout.splitlines():
            if line.startswith("?"):
                continue
            filename = line[3:]
            filenames.append(filename)
        return filenames

    def get_untracked_files(self):
        filenames = []
        exitcode, stdout = self.get_status_output(self._gitcmd(GIT_STATUS_PORCELAIN))
        if 'working directory clean' in stdout:
            return filenames
        for line in stdout.splitlines():
            if not line.startswith("?"):
                continue
            filename = line[3:]
            filenames.append(filename)
        return filenames

    def revert(self, args):
        if not args:
            self.run(self._gitcmd(GIT_REVERT_ALL))
        else:
            self.print_text("Revert %s" % format_shell_args(args))
            args = self.relative_filenames(args)
            self.run(self._gitcmd(GIT_REVERT_1 + args), ignore_exitcode=True, verbose=False)
            self.run(self._gitcmd(GIT_REVERT_2 + args), verbose=False)

    def _gitcmd(self, cmd):
        return (GIT_PROGRAM,) + ('--git-dir', self.gitdir) + cmd

    def _get_existing_files(self):
        output = self.get_output(self._gitcmd(GIT_LIST_FILES))
        output = output.strip()
        return output.splitlines()

SCM_CLASSES = dict((klass.SCM, klass) for klass in (RepositoryHG, RepositoryGIT))

def usage():
    print("usage: %s command" % sys.argv[0])
    print("")
    print("Available commands:")
    for commands in ALL_COMMANDS:
        print(' - ' + commands)
    sys.exit(1)

if __name__ == "__main__":
    Application().main()

