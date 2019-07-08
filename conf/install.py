#!/usr/bin/env python
from __future__ import with_statement
from os.path import dirname, realpath, join as path_join, expanduser, exists, islink
from os import stat, readlink, symlink, lstat, unlink, makedirs
from stat import S_ISLNK
from shutil import copyfile
from sys import exit, stdout, platform
from difflib import unified_diff
from errno import EEXIST
import subprocess


SYSTEMD = False
FILES = [
    'gdbinit',
    'gitconfig',
    'gvimrc',
    'hgrc',
    'screenrc',
    'vimrc',
    ('gtk.css', '.config/gtk-3.0/gtk.css'),
    ('python_scm_config', 'python/scm_config'),
]
if platform.startswith('freebsd'):
    FILES.append(('bashrc', '.bash_profile'))
else:
    FILES.append(('bashrc', '.bashrc'))
if SYSTEMD:
    FILES.append(('systemd_user/ssh-agent.service',
                  '.config/systemd/user/ssh-agent.service'))
    SYSTEMD_SERVICES = ['ssh-agent.service']


def create_symlinks():
    srcdir = realpath(dirname(__file__))
    home = expanduser('~')

    files = []
    for name in FILES:
        if isinstance(name, tuple):
            name, dstname = name
            dstname = path_join(home, dstname)
            dstdir = dirname(dstname)
            try:
                makedirs(dstdir, 0o700)
            except OSError as exc:
                if exc.errno == EEXIST:
                    pass
                else:
                    raise
            else:
                print("Create directories %s" % dstdir)
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

    for name, src, dst in files:
        try:
            lstat(dst)
        except OSError:
            pass
        else:
            # remove broken link
            unlink(dst)
        print("Link %s to %s" % (src, dst))
        symlink(src, dst)


def enable_systemd_services():
    for service in SYSTEMD_SERVICES:
        cmd = ['systemctl', '--user', 'enable', service]
        print("Run %s" % ' '.join(cmd))
        proc = subprocess.Popen(cmd)
        exitcode = proc.wait()
        if exitcode:
            exit(exitcode)


def main():
    create_symlinks()
    if SYSTEMD:
        enable_systemd_services()


if __name__ == "__main__":
    main()
