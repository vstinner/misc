#!/usr/bin/env python3
import errno
import fnmatch
import glob
import optparse
import os.path
import re
import shutil
import sys

FILE_EXT = {'avi', 'mp4'}
RENAME = (
    # (...)name.S01E04(...) => name.S01E04
    (re.compile(r"^.*?([a-z][a-z0-9_. ]*S[0-9]{2}E[0-9]{2}).*$", re.I), r"\1"),
    # (...)name(...) => name
    (re.compile(r"^.*?([a-z][a-z0-9_. ]*).*$" , re.I), r"\1"),
)
REMOVE_EXT = set(('html', 'txt'))

STRIP = (
    '.BRRip',
    '.FASTSUB',
    '.FRENCH',
    '.HDTV',
    '.MD',
    '.R6',
    '.VOSTFR',
    '.XViD-SHiFT',
    '.XviD',
    '.XviD-ARK01',
    '.XviD-SVR',
)


def copy_file(src, dst):
    try:
        # First try to create an hard link to reduce disk space
        os.link(src, dst)
    except OSError as exc:
        if exc.errno == errno.EXDEV:
            # Fallback to regular file copy
            shutil.copyfile(src, dst)
        else:
            raise


class Rename:
    def rename(self, directory, name):
        path = os.path.join(directory, name)
        name, ext = os.path.splitext(name)

        # "[...] name(...)" => " name(...).avi"
        name = re.sub(r'\[[^][]*\]', '', name)

        while True:
            modified = False
            for pattern in STRIP:
                if not name.endswith(pattern):
                    continue
                name = name[:-len(pattern)]
                modified = True
            if not modified:
                break

        # strip spaces
        name = name.strip()

        for regex, replace in RENAME:
            match = regex.search(name)
            if match is None:
                continue
            new_name = regex.sub(replace, name)
            break
        else:
            print("ERROR: Don't know how to rename %s" % path)
            sys.exit(1)

        new_path = os.path.join(self.dest_dir, new_name + ext)
        if new_path == path:
            return

        if os.path.exists(new_path):
            print("ERROR: File already exists %s" % new_path)
            print("Current path: %s" % path)
            sys.exit(1)

        if self.options.copy:
            print("Copy %s to %s" % (path, new_path))
            copy_file(path, new_path)
        elif self.options.move:
            print("Move %s to %s" % (path, new_path))
            os.rename(path, new_path)
        else:
            print("Copy/Rename %s to %s" % (path, new_path))

    def rename_dir(self, directory, is_subdir=False):
        names = os.listdir(directory)
        remove = is_subdir
        for name in names:
            ext = name.split('.')[-1].lower()
            path = os.path.join(directory, name)
            if ext not in FILE_EXT:
                if remove and ext not in REMOVE_EXT:
                    print("Keep %s: file %s" % (directory, name))
                    remove = False
                continue
            if os.path.isdir(path):
                remove = False
                sub_empty = self.rename_dir(path, True)
                remove = False
            else:
                self.rename(directory, name)
        if remove:
            print("Remove %s" % directory)
            if names:
                for name in names:
                    print("  file: %s" % name)
            else:
                    print("  (empty directory)")
            if self.options.remove:
                shutil.rmtree(directory)

    def parse_options(self):
        parser= optparse.OptionParser(
            description="Rename files downloaded by Torrent",
            usage="%prog [options] file1 [file2 ...]")
        parser.add_option(
            '--move', action="store_true",
            help='Really move files')
        parser.add_option(
            '--copy', action="store_true",
            help="Really copy files")
        parser.add_option(
            '--remove', action="store_true",
            help='Really remove "empty" subdirectories')
        parser.add_option(
            '-d', '--dest-dir', type='str',
            help='Destination directory (default: current directory)',
            default=os.getcwd())

        options, args = parser.parse_args()
        if not len(args):
            parser.print_help()
            sys.exit(1)

        return (options, args)

    def main(self):
        self.options, filenames = self.parse_options()
        self.dest_dir = self.options.dest_dir
        for filename in filenames:
            if not os.path.exists(filename):
                print("Warning: %s does not exist" % filename)
                continue
            if os.path.isdir(filename):
                self.rename_dir(filename)
            else:
                self.rename(os.path.dirname(filename), os.path.basename(filename))
        if not self.options.move and not self.options.copy:
            print("")
            print("Now run %s with --move/--copy to really move/copy files"
                  % sys.argv[0])

if __name__ == "__main__":
    Rename().main()
