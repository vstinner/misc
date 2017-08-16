VERSION=2.2.1
ROOT=$PWD
TGZ=expat-$VERSION.tar.bz2
DST=$PWD/Modules/expat

set -e -x

if [ ! -d "$DST" ]; then
    echo "Unable to find $DST"
    exit 1
fi

tar -xf $TGZ
SRC=$PWD/expat-$VERSION/

rm -rf $DST
mkdir $DST
cp $SRC/COPYING $DST/
cp $SRC/lib/*.[ch] $DST/

git checkout $DST/expat_config.h

# FIXME: Header file used to build expat DLL on Windows:
# "Namespace all expat exported symbols to avoid dynamic loading symbol
# collisions when embedding Python"
git checkout $DST/pyexpatns.h

echo "Directory $DST synchronized with Expat $VERSION from $TGZ"

echo 'FIXME: revert manually Modules/expat/expat_external.h change to add #include "pyexpatns.h"'
