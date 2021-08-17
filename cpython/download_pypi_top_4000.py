#!/usr/bin/python3
# Source: https://github.com/methane/notes/blob/master/2020/wchar-cache/download_sdist.py
#
# Download JSON from:
# https://hugovk.github.io/top-pypi-packages/
#
# Try:
# https://hugovk.github.io/top-pypi-packages/top-pypi-packages-30-days.min.json

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

def main():
    start_time = time.monotonic()

    if len(sys.argv) < 2:
        print("Usage: %s directory [count]" % sys.argv[0])
        sys.exit(1)
    dst_dir = sys.argv[1]
    if len(sys.argv) >= 3:
        count = int(sys.argv[2])
    else:
        count = None
    try:
        os.mkdir(dst_dir)
    except FileExistsError:
        pass

    projs = projects()
    if count:
        projs = projs[:count]
    nproject = len(projs)
    print(f"Project#: {nproject}")

    for index, proj in enumerate(projs):
        try:
            download_sdist(dst_dir, index, proj, nproject)
        except Exception:
            traceback.print_exc()
            print(f"Failed to download {proj}")

    dt = time.monotonic() - start_time
    print(f"Downloaded {nproject} projects in {dt:.1f} seconds")

if __name__ == "__main__":
    main()
