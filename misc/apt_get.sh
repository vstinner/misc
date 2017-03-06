#!/bin/bash

set -x -e

# terminal, editor
apt-get install less screen vim

# admin
apt-get install openssh-server sudo

# dev
#apt-get install subversion git-svn
apt-get install mercurial git-core manpages-dev
apt-get install gdb strace ltrace lsof valgrind
apt-get install exuberant-ctags
apt-get build-dep python

# dev GUI
apt-get install vim-gtk meld

# documentation
#apt-get install rst2pdf

# GUI
#apt-get install chromium-browser mplayer
#apt-get install python-qt4 python-m2crypto python-ipy qt4-dev-tools pyqt4-dev-tools
