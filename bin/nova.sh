#!/bin/sh
set -x
mplayer -quiet -cache 1024 http://broadcast.infomaniak.net:80/radionova-high.mp3 "$@"
