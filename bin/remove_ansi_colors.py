#!/usr/bin/env python3
import sys
import re


# "\033[1m"
RE_COLOR = re.compile(br'\033\[[0-9]{1,2}m')
# "\033[1;31m"
RE_BG_COLOR = re.compile(br'\033\[[0-9]{1,2};[0-9]{1,2}m')


def remove_ansi_colors(data):
    data = RE_COLOR.sub(b'', data)
    data = RE_BG_COLOR.sub(b'', data)
    return data


def main():
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        with open(filename, 'rb') as fp:
            data = fp.read()
    else:
        data = sys.stdin.buffer.read()
    data = remove_ansi_colors(data)
    sys.stdout.buffer.write(data)


if __name__ == "__main__":
    main()
