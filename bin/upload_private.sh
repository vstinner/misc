#!/bin/sh
set -e
echo "Upload $# files to ssh-haypo.alwaysdata.net:www/tmp"
scp -v -r "$@" haypo@ssh-haypo.alwaysdata.net:www/
for file in "$@"; do
    echo http://www.haypocalc.com/$(basename "$file")
done
