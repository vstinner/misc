MODULES="pip testtools virtualenv wheel"
#MODULES="$MODULES setuptools"
set -e -x
python2 -m pip install -U $MODULES tox
python3 -m pip install -U $MODULES vex twine
cp /usr/bin/pip2 /usr/bin/pip

echo
echo "XXX On Fedora, pip3 -m pip install -U setuptools breaks ensurepip"
echo "XXX and so venv. Fedora has a downstream ensurepip/rewheel/ which fails"
echo "XXX if there are multiple"
echo "XXX /usr/lib/python3.6/site-packages/setuptools-XXX.dist-info/"
echo "XXX directories."
