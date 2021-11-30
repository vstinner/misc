#!/usr/bin/python3
import sys
import os
import subprocess

pypi_dir = "pypi-top-5000_2021-08-17"
if 0:
    pattern_filename = sys.argv[1]
    with open(pattern_filename, encoding="utf8") as fp:
        pattern = fp.read().strip()
else:
    pattern = sys.argv[1]

def grep(filename, pattern):
    grep = ["grep", "--text", "-E", pattern]

    if filename.endswith((".tar.gz", ".tar.bz2", ".tgz")):
        decompress = ["tar", "-xO", "-f", fullname]
        continue
    elif filename.endswith((".zip",)):
        decompress = ["unzip", "-p", fullname]
    else:
        raise Exception(f"unsupported filename: {filename!r}")

    cmd1 = subprocess.Popen(decompress, stdout=subprocess.PIPE)
    cmd2 = subprocess.Popen(grep,
                            stdin=cmd1.stdout,
                            stdout=subprocess.PIPE,
                            text=True)
    stdout = cmd2.communicate()[0]

    exitcode1 = cmd1.wait()
    exitcode2 = cmd2.wait()
    if exitcode1:
        print(f"Failed to decompress {filename!r}")
        sys.exit(exitcode1)
    if exitcode2 not in (0, 1):
        print(f"grep command failed on {filename!r}: exit code {exitcode2}")
        sys.exit(exitcode2)

    return stdout

def main():
    projects = 0
    for filename in os.listdir(pypi_dir):
        filename = os.path.join(pypi_dir, filename)
        stdout = grep(filename, pattern)

        if stdout:
            print(f"=== {filename} ===")
            print(stdout.rstrip())
            print()
            projects += 1

    print(f"Matching projects: {projects}")


if __name__ == "__main__":
    main()
