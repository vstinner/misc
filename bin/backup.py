#!/usr/bin/env python
"""
Experimental script to backup my Linux PC between two disks.

Cleanup before backup:

 * run: scm.py clean
 * remove old/backup files? (ex: cleanup the trash)
"""
import datetime
import os
import subprocess
import sys

RSYNC = "rsync"

SRC_DISK = "/"
if 0:
    DEST_DISK = "/mount/sdc9"
    DIRECTORIES = (
        ("var/lib/libvirt", "var_lib_libvirt"),
    )
else:
    DEST_DISK = "/mount/sdc7"
    DIRECTORIES = (
        # TODO: exclude:
        # .local/share/Trash/
        # .kde/share/apps/amarok/albumcovers/cache/
        # .cache/google-chrome/Default/Cache/
        # .mozilla/firefox/*/Cache/
        # .thumbnails/
        ("home/haypo", "home_haypo"),
        ("etc", "etc"),
        ("data", "data"),
        ("root", "root"),
    )

# TODO: implement copy of a whole disk
# stop all services: courier, apache, mysql, ...
# sudo rsync \
#     --exclude /dev \
#     --exclude /proc \
#     --exclude /sys \
#     --exclude /tmp \
#     -a --update \
#     / haypo@lisa:/data/marge

# TODO: copy though network
# ssh root@homer "cd /; tar -cjsp etc"|cpipe -vw|tar -xj
#
# (cd /; sudo tar --exclude=dev --exclude=proc --exclude=var/run --exclude=var/cache --exclude=sys -c .)|nc lisa 12345


def format_shell_arg(arg):
    if ' ' in arg:
        return '"%s"' % arg
    else:
        return arg

def format_shell_args(args):
    return ' '.join(format_shell_arg(arg) for arg in args)

class Backup:
    def __init__(self):
        self.verbose = True
        # delete is only useful is the transfer was interrupted and has to
        # be finished. by default, the transfer is restarted from zero.
        self.delete = False
        self.prune = False
        self.src_disk = SRC_DISK
        self.dst_disk = DEST_DISK

    def info(self, message=""):
        if message:
            now = datetime.datetime.now()
            now = str(now).split(".")[0]
            message = "%s: %s" % (now, message)
        print(message)

    def copy(self, src, dst):
        args = [RSYNC,
            # archive mode; equals -rlptgoD (no -H,-A,-X)
            # -r, --recursive   recurse into directories
            # -l, --links       copy symlinks as symlinks
            # -p, --perms       preserve permissions
            # -t, --times       preserve modification times
            # -g, --group       preserve group
            # -o, --owner       preserve owner (super-user only)
            # -D                same as --devices --specials
            # --devices         transfer character and block device files
            #                   to the remote system to recreate these devices
            # --specials        transfer special files such as named sockets
            #                   and fifos
            "--archive",
            # don't cross filesystem boundaries
            "--one-file-system"]
        if self.verbose:
            args.extend(("--progress", "--verbose"))
        if self.delete:
            args.append("--delete")

        src = os.path.join(self.src_disk, src)
        args.append(src)
        dst = os.path.join(self.dst_disk, dst)
        args.append(dst)

        self.info("Run command: %s" % format_shell_args(args))
        if not self.prune:
            exitcode = subprocess.call(args)
            if exitcode:
                info("Command failed with exit code %s: %s" % (exitcode, format_shell_args(args)))
                sys.exit(exitcode)

    def main(self):
        now = datetime.datetime.now()
        timestamp = now.strftime("backup-%Y-%m-%d")
        self.dst_disk = os.path.join(self.dst_disk, timestamp)
        self.info("Make directory: %s" % self.dst_disk)
        if os.path.isdir(self.dst_disk):
            print("Destination directory exists: %s" % self.dst_disk)
            question = raw_input("If you want to restart an interrupted transfer, please write YES: ")
            if question.strip() != "YES":
                sys.exit(1)
            self.info()

            self.delete = True
        else:
            question = raw_input("Create a new backup into %s? please write YES: " % self.dst_disk)
            if question.strip() != "YES":
                sys.exit(1)
            self.info()

            if not self.prune:
                os.mkdir(self.dst_disk)

        for index, item in enumerate(DIRECTORIES):
            src, dst = item
            self.info("[%s/%s] Copy %s" % (1 + index, len(DIRECTORIES), src))
            self.copy(src, dst)
            self.info()

        self.info("Backup done successfully")

if __name__ == "__main__":
    Backup().main()

