#!/usr/bin/env python3
import argparse
import binascii
import hashlib
import math
import os.path
import queue
import sys
import threading


CHUNK_SIZE = 128 * 1024


def hash_file(filename, callback):
    filehash = hashlib.md5()
    with open(filename, "rb") as fp:
        while True:
            chunk = fp.read(CHUNK_SIZE)
            if not chunk:
                break
            filehash.update(chunk)
    return filehash.digest()



class HashThread(threading.Thread):
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def run(self):
        while True:
            job = self.queue.get()
            if job is None:
                break
            filename, callback = job
            checksum = hash_file(filename, callback)
            callback(checksum)


HEADER = "dedup.py 0.0 md5"


class App:
    def __init__(self):
        self.cache_filename = '~/.cache/deduppy_cache.txt'
        self.cache = {}
        self.queue = None
        self.threads = []
        self.max_threads = os.cpu_count() or 1

    def read_cache(self):
        try:
            fp = open(self.cache_filename, 'rb')
        except FileNotFoundError:
            return

        with fp:
            header = fp.readline()
            if header != HEADER.encode() + b'\n':
                print("ERROR: invalid header in cache file: %s: %a"
                      % (self.cache_filename, header))
                sys.exit(1)

            for line in fp:
                line = line.rstrip(b'\n')
                mtime, checksum, filename = line.split(b':', 2)
                checksum = binascii.unhexlify(checksum)
                mtime = float(mtime)
                self.cache[filename] = (mtime, checksum)

        print("Read cache file from %s (%s files)"
              % (os.fsdecode(self.cache_filename), len(self.cache)))

    def write_cache(self):
        if not self.cache:
            return

        with open(self.cache_filename, 'wb') as fp:
            fp.write(HEADER.encode() + b'\n')
            for filename, entry in self.cache.items():
                mtime, checksum = entry
                checksum = binascii.hexlify(checksum)
                # Round towards minus infinity, unit of one second
                mtime = math.floor(mtime)
                line = b'%i:%s:%s\n' % (mtime, checksum, filename)
                fp.write(line)
            fp.flush()

        print("Write cache file into %s (%s files)"
              % (os.fsdecode(self.cache_filename), len(self.cache)))

    def parse_args(self):
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest='action')

        scan = subparsers.add_parser('scan')
        scan.add_argument('directory', nargs='+')

        self.args = parser.parse_args()

    def real_path(self, path):
        return os.path.realpath(path)

    def warn(self, msg):
        print("WARNING: msg")

    def hash_result_cb(self, filename, mtime, checksum):
        self.cache[filename] = (mtime, checksum)

    def scan_file(self, path):
        path = self.real_path(path)
        if path == self.cache_filename:
            return
        if b'\n' in path:
            raise ValueError("filename contains a newline: %r" % path)
        if not os.path.isfile(path):
            self.warn("Skip non-regular file: %s" % os.fsdecode(path))

        filestat = os.stat(path)
        mtime = filestat.st_mtime

        if path in self.cache:
            cache_mtime, checksum = self.cache[path]
            if cache_mtime >= mtime:
                return

        def write_cache(checksum):
            self.cache[path] = (mtime, checksum)

        job = (path, write_cache)
        size = filestat.st_size / (1024.0 ** 2)
        if size >= 1024:
            size = "%.1f GB" % (size / 1024.0)
        else:
            size = "%.1f MB" % size
        print("Hash %s (%s)" % (os.fsdecode(path), size))
        self.queue.put(job)

    def scan_directory(self, directory):
        directory = os.fsencode(directory)
        for rootdir, dirs, filenames in os.walk(directory):
            for filename in filenames:
                path = os.path.join(rootdir, filename)
                self.scan_file(path)

    def scan(self):
        for directory in self.args.directory:
            self.scan_directory(directory)

    def start_threads(self):
        nthread = os.cpu_count() or 1
        self.queue = queue.Queue(nthread)
        while len(self.threads) < nthread:
            thread = HashThread(self.queue)
            thread.start()
            self.threads.append(thread)

    def stop_threads(self):
        for thread in self.threads:
            self.queue.put(None)
        for thread in self.threads:
            thread.join()

    def main(self):
        self.cache_filename = os.path.expanduser(self.cache_filename)
        self.cache_filename = self.real_path(self.cache_filename)
        self.cache_filename = os.fsencode(self.cache_filename)

        self.parse_args()
        self.read_cache()
        self.start_threads()
        if self.args.action == 'scan':
            self.scan()
        self.stop_threads()
        self.write_cache()


if __name__ == "__main__":
    App().main()
