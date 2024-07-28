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
from concurrent.futures import ThreadPoolExecutor


try:
    from termcolor import cprint
except ImportError:
    print("Warning: termcolor is missing, install it with: python -m pip install --user termcolor", file=sys.stderr)
    print(file=sys.stderr)

    def cprint(msg, *ignored):
        print(msg)


session = requests.Session()

JSON_URL = 'https://hugovk.github.io/top-pypi-packages/top-pypi-packages-30-days.min.json'


def projects():
    cprint(f"Download JSON from: {JSON_URL}", "green")
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
        cprint(f"Cannot find URL for project: {proj}", "red")
        return
    filename = url[url.rfind('/')+1:]
    filename = os.path.join(dst_dir, filename)
    if os.path.exists(filename):
        cprint(f"Exists: {filename}", "yellow")
        return
    resp = session.get(url)
    resp.raise_for_status()
    content = resp.content
    cprint(f"[{index}/{nproject}] "
           f"Saving to {filename} ({len(content) / 1024.:.1f} kB)", "green")
    with open(filename, "wb") as f:
        f.write(content)


def parse_args():
    parser = argparse.ArgumentParser(description='Download the source code of PyPI top projects.')
    parser.add_argument('dst_dir', metavar="DIRECTORY",
                        help='Destination directory')
    parser.add_argument('count', metavar='COUNT', type=int, nargs='?',
                        help='Only download the top COUNT projects')
    parser.add_argument('-j', '--jobs', metavar='N', type=int, default=8,
                        help='run N download jobs in parallel (default: %(default)s)')

    return parser.parse_args()


def main():
    args = parse_args()
    dst_dir = args.dst_dir
    count = args.count
    start_time = time.monotonic()

    try:
        os.mkdir(dst_dir)
    except FileExistsError:
        pass

    projs = projects()
    if count:
        projs = projs[:count]
    nproject = len(projs)
    print(f"Project#: {nproject}")

    def download_wrapper(args):
        dst_dir, index, proj, nproject = args
        try:
            download_sdist(dst_dir, index, proj, nproject)
        except Exception:
            traceback.print_exc()
            cprint(f"Failed to download {proj}", "red")

    max_workers = args.jobs
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        wrapper_args = [
            (dst_dir, index, proj, nproject) for index, proj in enumerate(projs, start=1)]
        for _ in executor.map(download_wrapper, wrapper_args):
            pass

    dt = time.monotonic() - start_time
    cprint(f"Downloaded {nproject} projects in {dt:.1f} seconds", "green")


if __name__ == "__main__":
    main()
