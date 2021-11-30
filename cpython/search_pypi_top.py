#!/usr/bin/python3 -u
import re
import sys
import os
import subprocess

pypi_dir = "PYPI-TOP-5000"
if 0:
    pattern_filename = sys.argv[1]
    with open(pattern_filename, encoding="utf8") as fp:
        pattern = fp.read().strip()
else:
    pattern = os.fsencode(sys.argv[1])

print(pattern)

def grep(filename, pattern):
    regex = re.compile(pattern)

    if filename.endswith((".tar.gz", ".tar.bz2", ".tgz")):
        decompress = ["tar", "-xO", "-f", filename]
    elif filename.endswith((".zip",)):
        decompress = ["unzip", "-p", filename]
    else:
        raise Exception(f"unsupported filename: {filename!r}")

    cmd1 = subprocess.Popen(decompress, stdout=subprocess.PIPE)

    found = []
    for line in cmd1.stdout:
        if regex.search(line):
            found.append(line)

    exitcode1 = cmd1.wait()
    if exitcode1:
        print(f"Failed to decompress {filename!r}")
        sys.exit(exitcode1)

    return found

def main():
    projects = 0
    #for filename in os.listdir(pypi_dir):
    filename = 'PYPI-TOP-5000/scipy-1.7.3.tar.gz'
    if 1:
        #filename = os.path.join(pypi_dir, filename)
        lines = grep(filename, pattern)

        if lines:
            print(f"=== {filename} ===")
            for line in lines:
                line = line.decode('utf8', 'replace').strip()
                print(line)
            print()
            projects += 1
        #break

    print(f"Matching projects: {projects}")


if __name__ == "__main__":
    main()
