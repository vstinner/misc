#!/usr/bin/env python
from __future__ import with_statement
from os.path import dirname, realpath, join as path_join, expanduser, exists, islink
from os import stat, readlink, symlink, lstat, unlink, makedirs
from stat import S_ISLNK
from shutil import copyfile
from sys import exit, stdout
from difflib import unified_diff
from errno import EEXIST

FILES = (
    'bashrc',
    'gdbinit',
    'gitconfig',
    'gvimrc',
    'hgrc',
    'screenrc',
    'vimrc',
    ('gtk.css', '.config/gtk-3.0'),
)

def main():
    srcdir = realpath(dirname(__file__))
    home = expanduser('~')

    files = []
    for name in FILES:
        if isinstance(name, tuple):
            name, dstdir = name
            dstdir = path_join(home, dstdir)
            try:
                makedirs(dstdir, 0o700)
            except OSError as exc:
                if exc.errno == EEXIST:
                    pass
                else:
                    raise
            else:
                print("Create directory: %s" % dstdir)
            dstname = name
        else:
            dstdir = home
            dstname = '.' + name
        src = path_join(srcdir, name)
        dst = path_join(dstdir, dstname)
        try:
            dst_link = readlink(dst)
        except OSError:
            pass
        else:
            if dst_link == src:
                continue
        files.append((name, src, dst))

    err = False
    for name, src, dst in files:
        if (not exists(dst)) or islink(dst):
            continue
        err = True
        print("Error: %s already exists" % dst)
        with open(src) as fp:
            src_lines = fp.readlines()
        with open(dst) as fp:
            dst_lines = fp.readlines()
        for line in unified_diff(src_lines, dst_lines, src, dst):
            stdout.write(line)
        print
    if err:
        exit(1)

    if not files:
        print("Nothing to do (symlinks already created).")
        exit(0)

    for name, src, dst in files:
        try:
            lstat(dst)
        except OSError:
            pass
        else:
            # remove broken link
            unlink(dst)
        print("Create %s" % dst)
        symlink(src, dst)

if __name__ == "__main__":
    main()

