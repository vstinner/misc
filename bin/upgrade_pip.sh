MODULES="pip virtualenv wheel"
#MODULES="$MODULES setuptools"
set -e -x
python2 -m pip install --user -U $MODULES tox
python3 -m pip install --user -U $MODULES vex twine
#cp /usr/bin/pip2 /usr/bin/pip
# pip is now Python 3

# echo
# echo "XXX On Fedora, pip3 -m pip install -U setuptools breaks ensurepip"
# echo "XXX and so venv. Fedora has a downstream ensurepip/rewheel/ which fails"
# echo "XXX if there are multiple"
# echo "XXX /usr/lib/python3.6/site-packages/setuptools-XXX.dist-info/"
# echo "XXX directories."
# echo
# echo "Workaround:"
# echo "sudo python3 -m pip uninstall setuptools"
# echo "sudo dnf reinstall python3-setuptools"
