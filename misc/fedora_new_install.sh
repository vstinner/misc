# http://doc.fedora-fr.org/wiki/Lecture_de_fichiers_multimédia#Mplayer
# http://doc.fedora-fr.org/wiki/Lecture_de_fichiers_multim%C3%A9dia
# http://doc.fedora-fr.org/wiki/Flash_:_installation_du_plugin_propri%C3%A9taire
# http://doc.fedora-fr.org/wiki/D%C3%A9p%C3%B4t_Fedora_Chromium

# net-tools: netstat command

# deltarpm: faster dnf update

# default system
# bind-utils: host command
dnf install \
    bind-utils

# TODO: libvirtXXX
dnf install \
    deltarpm \
    less wget screen ctags-etags vim-enhanced gvim \
    net-tools nc \
    man-pages-fr mercurial git-core patch diffstat \
    sshfs \
    make gcc gdb \
    procps sysstat perf lsof strace ltrace valgrind \
    yum-utils \
    gimp \
    gstreamer-ffmpeg gstreamer-plugins-bad gstreamer-plugins-ugly \
    @virtualization virt-manager \
    libreoffice-langpack-fr libreoffice-impress \
    aajohan-comfortaa-fonts.noarch
#yum install bzip2-devel ncurses-devel openssl-devel readline-devel sqlite-devel
    # yum-utils: yum-builddep

yum-builddep python
dnf install pyflakes python-devel python3-devel meld

# http://doc.fedora-fr.org/wiki/Dépôt_RPM_Fusion
# dnf install mplayer

# dnf install --nogpgcheck http://linuxdownload.adobe.com/adobe-release/adobe-release-x86_64-1.0-1.noarch.rpm
# dnf install flash-plugin
