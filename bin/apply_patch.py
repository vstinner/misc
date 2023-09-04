#!/usr/bin/env python3
"""
Apply a patch.

Usage:

* File: "apply_patch.py fix.patch"
* URL: "apply_patch.py http://example.com/fix.patch"
* Reverse: "apply_patch.py -R fix.patch" or "apply_patch.py --reverse fix.patch"

Features:

* Automatically guess the "-p" option. For levels different than -p0, ask
  for confirmation.
* If the patch doesn't match: ask for confirmation before changing files
  and creating .org and .rej files
* The command line parameter can be an URL! http and https are supported
  using Python builtin urllib module.

The program supports Python 2 and Python 3.

TODO: handle correctly patch creating new files. Don't duplicate the content
of a file.

The "patch" program is still required. The patch program must support
--dry-run.

Distributed under the GNU GPL license version 3 or later.
"""
from __future__ import with_statement
import os
import subprocess
import sys
import tempfile
try:
    from urllib.request import urlopen, Request
except ImportError:
    from urllib2 import urlopen, Request

PY3 = (sys.version_info >= (3,))
MAX_PATH_DIFF = 6
IGNORE_DIRECTORIES = set(('.hg', '.git', 'build', '__pycache__'))
PATCH_PROGRAM = 'patch'
SEPARATORS = (
    'index ',
    '===========================================================',
    'diff ',
)
PREFIXES = ("index ", "new file mode ", "deleted file mode ")

def parse_filenames(filename):
    step = input_filename = output_filename = None
    with open(filename) as patch:
        line_number = 0
        for line in patch:
            line_number += 1
            line = line.rstrip()
            if step == 'input_file':
                if line.startswith("--- "):
                    # split by space or tab
                    input_filename = line[4:] #.split(None, 1)[0]
                    step = 'output_file'
                elif any(line.startswith(prefix) for prefix in PREFIXES):
                    # ignore "index 4bb3c01..9e84d63 100644"
                    # ignore "new file mode 100644"
                    # ignore "deleted file mode 100644"
                    pass
                else:
                    raise ValueError("Input filename line %s doesn't start with ---" % line_number)
            elif step == 'output_file':
                if not line.startswith("+++ "):
                    raise ValueError("Output filename line doesn't start with +++: %r" % line)
                # split by space or tab
                output_filename = line[4:] #.split(None, 1)[0]
                yield (input_filename, output_filename)
                step = None
            else:
                if any(line.startswith(separator) for separator in SEPARATORS):
                    step = 'input_file'

def strip_filename(filename, level):
    parts = filename.split(os.path.sep)
    parts = parts[level:]
    return os.path.sep.join(parts)

def _scanlevel(root, filenames):
    best = None
    for level in range(MAX_PATH_DIFF):
        failure = 0
        for in_fn, out_fn in filenames:
            if in_fn == '/dev/null':
                # new file: check the output directory
                filename = os.path.dirname(out_fn)
            else:
                if out_fn == '/dev/null':
                    # deleted file
                    filename = in_fn
                else:
                    filename = out_fn
            filename = strip_filename(filename, level)
            if filename:
                filename = os.path.join(root, filename)
            if not os.path.exists(filename):
                failure += 1
        if not failure:
            return (level, False)
        if not best or best[1] > failure:
            best = (level, failure)
    if best[1] == len(filenames):
        return (None, True)
    else:
        print("Warning: scanning patch level tolerates %s/%s failures" % (best[1], len(filenames)))
        return (best[0], True)

def _search_directory(guess, parentdir, patch_filenames):
    found = False
    for name in os.listdir(parentdir):
        if name in ('.', '..'):
            continue
        if name in IGNORE_DIRECTORIES:
            continue
        fullname = os.path.join(parentdir, name)
        if not os.path.isdir(fullname):
            continue
        sys.stdout.write("."); sys.stdout.flush()
        if _search_directory(guess, fullname, patch_filenames):
            continue

        level, error = _scanlevel(fullname, patch_filenames)
        if level is not None:
            guess.append((fullname, level))
            if not error:
                found = True
    return found

def search_directory(patch_filenames):
    stdout = sys.stdout
    stdout.write("Search for a match in subdirectories"); stdout.flush()
    guess = []
    _search_directory(guess, '.', patch_filenames)
    stdout.write("\n"); stdout.flush()
    return guess

def scanlevel(patch):
    filenames = list(parse_filenames(patch))
    if not filenames:
        print("Error: unable to parse filenames")
        sys.exit(1)

    level, error = _scanlevel('.', filenames)
    if level is not None:
        return level

    print("Unable to find patch level of the following filenames:")
    for in_fn, out_fn in filenames:
        print("> %s" % out_fn)
    print("")
    guess = search_directory(filenames)
    if len(guess) == 1:
        root, level = guess[0]
        print("Patch looks to fit in directory %s (level %s)" % (root, level))
        ask_confirmation("Apply patch from directory %s (y/N)?" % root)
        os.chdir(root)
        return level
    elif guess:
        print("You may try from directories:")
        for root, level in guess:
            print("%s (level %s)" % (root, level))
    else:
        print("Sorry, no matching subdirectory.")
    sys.exit(1)

def ask_confirmation(prompt):
    try:
        if PY3:
            answer = input(prompt)
        else:
            answer = input(prompt)
    except (KeyboardInterrupt, EOFError):
        print("no")
        sys.exit(1)
    answer = answer.lower().strip()
    if answer != 'y':
        sys.exit(1)

def downloadPatch(url, filename):
    request = Request(url)
    url = urlopen(request)
    data = url.read()
    fp = open(filename, "wb")
    fp.write(data)
    fp.close()

def usage():
    print("usage: %s [-R|--reverse] patch" % sys.argv[0])
    print("patch can be a file name or an URL.")

def main():
    tmpfile = None
    reverse = False
    if len(sys.argv) == 2:
        filename = sys.argv[1]
    elif len(sys.argv) == 3:
        if sys.argv[1] not in ('-R', '--reverse'):
            usage()
            sys.exit(1)
        reverse = True
        filename = sys.argv[2]
    else:
        usage()
        sys.exit(1)
    try:
        if filename.startswith(('http://', 'https://')):
            tmpfile = tempfile.NamedTemporaryFile()
            downloadPatch(filename, tmpfile.name)
            filename = tmpfile.name

        filename = os.path.realpath(filename)
        if not os.path.exists(filename):
            print("ERROR: Patch %s doesn't exist." % filename)
            sys.exit(1)
        level = scanlevel(filename)
        print("Patch level: %s" % level)

        # --dry-run: don't change any files
        # --batch: suppress questions
        command = [PATCH_PROGRAM, '--dry-run', '--batch']
        if reverse:
            # Revert a patch
            command.append('--reverse')
        else:
            # ask to not try to apply the patch backward
            command.append('--forward')
        command.extend(['-p%s' % level, '-i', filename])
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except OSError as err:
            print("Fail to run %s: %s" % (' '.join(command), err))
            sys.exit(1)
        stdout, stderr = process.communicate()
        returncode = process.wait()

        if returncode:
            if PY3:
                sys.stdout.flush()
                sys.stdout.buffer.write(stdout)
                sys.stdout.buffer.flush()
            else:
                sys.stdout.write(stdout)
            print
            ask_confirmation("Dry run failed. Apply anyway (y/N)?")

        command = [PATCH_PROGRAM, '--forward']
        if reverse:
            command.append('-R')
        command.extend(['-p%s' % level, '-i', filename])
        process = subprocess.Popen(command)
        returncode = process.wait()
    finally:
        if tmpfile is not None:
            tmpfile.close()
    if returncode:
        print("Patch failed.")
    else:
        print("Patch applied correctly.")
    sys.exit(returncode)


main()
