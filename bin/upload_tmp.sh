#!/bin/sh
set -e
echo "Upload $# files to ssh-haypo.alwaysdata.net:www/tmp"
scp -v -i ~/perso -r "$@" haypo@ssh-haypo.alwaysdata.net:www/tmp
for file in "$@"; do
    echo http://haypo.alwaysdata.net/tmp/$(basename "$file")
done
