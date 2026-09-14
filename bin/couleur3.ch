#!/bin/sh
set -x

# URL list: http://www.broadcast.ch/portal.aspx?pid=564&lang=fr
URL=http://stream.srg-ssr.ch/m/couleur3/mp3_128
CACHE=1024


while true; do
    # mplayer -prefer-ipv4 -ao pulse -quiet -cache $CACHE "$URL" "$@"
    mpv -quiet "$URL" "$@"
    echo "--- error! sleep... ---"
    sleep 2
done
