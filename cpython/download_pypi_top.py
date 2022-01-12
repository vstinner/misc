#!/usr/bin/python3
# Source: https://github.com/methane/notes/blob/master/2020/wchar-cache/download_sdist.py
# Source: https://github.com/methane/notes/tree/master/2020/wchar-cache
#
# Shell script:
# ---
# if [ -z "$1" ]; then
#     echo "usage: $0 pattern"
#     exit 1
# fi
# rg -zl "$1" pypi-top-5000_2021-08-17/*.{zip,gz,bz2,tgz}
# ---
#
# Download JSON from:
# https://hugovk.github.io/top-pypi-packages/
#
# Try:
# https://hugovk.github.io/top-pypi-packages/top-pypi-packages-30-days.min.json

import argparse
import requests
import traceback
import json
import os
import sys
import time

session = requests.Session()

JSON_URL = 'https://hugovk.github.io/top-pypi-packages/top-pypi-packages-30-days.min.json'


def projects():
    print("Download JSON from: %s" % JSON_URL)
    resp = session.get(JSON_URL)
    resp.raise_for_status()
    top = json.loads(resp.content)
    return [p["project"] for p in top["rows"]]

def find_url(proj):
    resp = session.get(f"https://pypi.org/pypi/{proj}/json")
    resp.raise_for_status()
    data = resp.json()
    for entry in data["urls"]:
        if entry["packagetype"] == "sdist":
            return entry["url"]
    return None

def download_sdist(dst_dir, index, proj, nproject):
    url = find_url(proj)
    if not url:
        # Universal wheel only, maybe.
        print(f"Cannot find URL for project: {proj}")
        return
    filename = url[url.rfind('/')+1:]
    filename = os.path.join(dst_dir, filename)
    if os.path.exists(filename):
        print(f"Exists: {filename}")
        return
    resp = session.get(url)
    resp.raise_for_status()
    content = resp.content
    print(f"[{index}/{nproject}] "
          f"Saving to {filename} ({len(content) / 1024.:.1f} kB)")
    with open(filename, "wb") as f:
        f.write(content)

def parse_args():
    parser = argparse.ArgumentParser(description='Download the source code of PyPI top projects.')
    parser.add_argument('pypi_dir', metavar="PYPI_DIRECTORY",
                        help='PyPI local directory')
    parser.add_argument('count', metavar='COUNT', type=int, nargs='?',
                        help='Only download the top N projects')

    return parser.parse_args()


def main():
    args = parse_args()
    start_time = time.monotonic()

    try:
        os.mkdir(args.pypi_dir)
    except FileExistsError:
        pass

    projs = projects()
    if args.count:
        projs = projs[:args.count]
    nproject = len(projs)
    print(f"Project#: {nproject}")

    for index, proj in enumerate(projs):
        try:
            download_sdist(args.pypi_dir, index, proj, nproject)
        except Exception:
            traceback.print_exc()
            print(f"Failed to download {proj}")

    dt = time.monotonic() - start_time
    print(f"Downloaded {nproject} projects in {dt:.1f} seconds")

if __name__ == "__main__":
    main()
