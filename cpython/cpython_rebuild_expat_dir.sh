TAG=R_2_2_8
ROOT=$PWD
# Checkout of the https://github.com/libexpat/libexpat/ project
LIBEXPAT=/home/vstinner/libexpat/
DST=$PWD/Modules/expat

set -e -x

if [ ! -d "$DST" ]; then
    echo "Unable to find $DST"
    exit 1
fi

cd $LIBEXPAT
git reset --hard
git clean -fdx
git checkout $TAG
SRC=$PWD/expat/

cd $ROOT

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
