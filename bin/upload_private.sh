#!/bin/sh
set -e
echo "Upload $# files to ssh.alwaysdata.com:www/"
scp -v -r "$@" haypo@ssh.alwaysdata.com:www/
for file in "$@"; do
    echo http://www.haypocalc.com/$(basename "$file")
done
