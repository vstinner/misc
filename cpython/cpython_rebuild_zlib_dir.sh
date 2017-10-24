VERSION=1.2.11
PYTHON=$PWD
TGZ="zlib-$VERSION.tar.gz"
URL="https://zlib.net/$TGZ"
# FIXME: fix GPG, https://zlib.net/zlib-1.2.11.tar.xz.asc
DST=$PYTHON/Modules/zlib

set -e -x

if [ ! -d "$DST" ]; then
    echo "Unable to find $DST"
    exit 1
fi

if [ ! -e "$TGZ" ]; then
    wget $URL
fi

tar -xf $TGZ
SRC=$PYTHON/zlib-$VERSION/

rm -rf $DST
mkdir $DST
# cp $SRC/COPYING $DST/
cp $SRC/* $DST/ ||:
cp $SRC/test/minigzip.c $DST/
cp $SRC/test/example.c $DST/
cp $SRC/doc/algorithm.txt $DST/

echo "Directory $DST synchronized with Expat $VERSION from $TGZ"

echo 'FIXME: revert manually Modules/expat/expat_external.h change to add #include "pyexpatns.h"'
