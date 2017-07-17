# cd /
# btrfs subvolume create backup

# Subvolumes relative to /
SRC_ROOT=/btrfs
DEST=/btrfs/snapshots
SOURCES="data"

DATE=$(python3 -c 'import datetime; now=datetime.datetime.now(); print(now.strftime("%Y-%m-%d"))')

echo "Create backup with the timestamp: $DATE"

set -x
set -e

for SOURCE in $SOURCES; do
    DIR=$DEST/${SOURCE}_$DATE
    if [ -e $DIR ]; then
        echo "Error: $DIR already exist"
        exit 1
    fi
    # -r: create readonly snapshot
    btrfs subvolume snapshot -r $SRC_ROOT/$SOURCE $DIR
done

set +x

echo

echo "Subvolumes:"
btrfs subvolume list $DEST

