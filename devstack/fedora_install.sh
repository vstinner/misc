# Install Fedora using "network install" and select "Minimal"

# Set locale to en_US
sudo localectl set-locale LANG=en_US.UTF-8

# To install DevStack
sudo yum install git

#  sudo yum install fedora-easy-karma
#  sudo yum install bodhi
#  sudo yum install bodhi-client

# For my own usage
sudo yum install mercurial

# Missing dependency for neutron
sudo yum install net-tools

# To develop on OpenStack
sudo yum install git-review

# To run OpenStack unit tests
sudo pip install tox==1.6.1

# To install Python 2 & 3 modules written in C
sudo yum install python-devel python3-devel

# To run SQLAchemty tests
sudo yum install mariadb-devel

# To run OpenStack tests
sudo pip install tox=1.6.1

# To install zmq
sudo pip install gcc-c++
