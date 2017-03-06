# cd /
# btrfs subvolume create backup

# Subvolumes relative to /
DEST=backup
SOURCES="home data"

DATE=$(python3 -c 'import datetime; now=datetime.datetime.now(); print(now.strftime("%Y-%m-%d"))')

echo "Create backup with the timestamp: $DATE"

set -x
set -e

for SOURCE in $SOURCES; do
    # -r: create readonly snapshot
    DIR=/$DEST/${SOURCE}_$DATE
    if [ -e $DIR ]; then
        echo "Error: $DIR already exist"
        exit 1
    fi
    btrfs subvolume snapshot -r /$SOURCE $DIR
done

set +x

echo

echo "Subvolumes:"
btrfs subvolume list /$DEST

