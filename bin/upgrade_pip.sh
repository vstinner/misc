MODULES="pip testtools setuptools virtualenv wheel"
set -e -x
python2 -m pip install -U $MODULES tox
python3 -m pip install -U $MODULES vex twine
cp /usr/bin/pip2 /usr/bin/pip
