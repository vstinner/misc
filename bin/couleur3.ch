#!/bin/sh
set -x
# -ao alsa

# URL list: http://www.broadcast.ch/portal.aspx?pid=564&lang=fr
URL=http://stream.srg-ssr.ch/m/couleur3/mp3_128


while true; do
    mplayer -prefer-ipv4 -ao pulse -quiet -cache 1024 "$URL" "$@"
    echo "--- error! sleep... ---"
    sleep 2
done
