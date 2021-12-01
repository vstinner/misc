#!/usr/bin/python3 -u
import os
import re
import sys
import tarfile
import zipfile


pypi_dir = "PYPI-2021-12-01-TOP-5000"
IGNORED_FILE_EXTENSIONS = (".so,")


def decompress_tar(filename, mode):
    with tarfile.open(filename, mode) as tar:
        while True:
            member = tar.next()
            if member is None:
                break
            name = member.name
            if name.endswith(IGNORED_FILE_EXTENSIONS):
                continue
            fp = tar.extractfile(member)
            if fp is None:
                continue
            yield (name, fp)


def decompress_zip(filename):
    with zipfile.ZipFile(filename) as zf:
        for member in zf.filelist:
            name = member.filename
            if name.endswith(IGNORED_FILE_EXTENSIONS):
                continue
            fp = zf.open(member)
            yield (name, fp)


def decompress(filename):
    if filename.endswith((".tar.gz", ".tgz")):
        yield from decompress_tar(filename, "r:gz")
    elif filename.endswith(".tar.bz2"):
        yield from decompress_tar(filename, "r:bz2")
    elif filename.endswith(".zip"):
        yield from decompress_zip(filename)
    else:
        raise Exception(f"unsupported filename: {filename!r}")


def grep(filename, pattern):
    regex = re.compile(pattern)

    found = []
    for name, fp in decompress(filename):
        for line in fp:
            if regex.search(line):
                found.append((name, line))

    return found

def main():
    arg = sys.argv[1]
    if 0:
        pattern_filename = arg
        with open(pattern_filename, encoding="utf8") as fp:
            pattern = fp.read().strip()
    else:
        pattern = os.fsencode(arg)

    total = 0
    for filename in os.listdir(pypi_dir):
        filename = os.path.join(pypi_dir, filename)
        print(f"# grep {filename}", file=sys.stderr)
        lines = grep(filename, pattern)

        if lines:
            for name, line in lines:
                line = line.decode('utf8', 'replace').strip()
                print(f"{filename}: {name}: {line}")
            total += len(lines)

    if total:
        print()
    print(f"Found {total} matching lines")


if __name__ == "__main__":
    main()
