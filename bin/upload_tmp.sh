#!/bin/sh
set -e
echo "Upload $# files to ssh.alwaysdata.com:www/tmp"
scp -v -r "$@" haypo@ssh.alwaysdata.com:www/tmp
for file in "$@"; do
    echo http://www.haypocalc.com/tmp/$(basename "$file")
done
