#!/bin/bash -x

# make sure this device is compatible
arch=`uname -m`
if [[ "$arch" != "aarch64" && "$arch" != "x86_64" ]]
then
    echo "ERROR -- RING requires architecture aarch64 or x86_64, however this machine is ${arch}"
    exit -1
fi

# make sure there is enough space on the device
MIN_SPACE=10
free_space=`df | grep /$ | awk '{print $4/(1000*1000)}'`
is_full=`echo "$free_space $MIN_SPACE" | awk '{if($1 <= $2) print "true"; else print "false";}'`
if [ $is_full == "true" ]
then
    echo "ERROR -- Low hard disk space detected ($free_space <= $MIN_SPACE)."
    exit -1
fi
echo "Current free space on hard disk: $free_space GB"

curdir=`pwd`
cd $HOME

# install neccessarry packages
sudo apt-get update

hash python3 > /dev/null 2>&1
if [ $? -eq 1 ]
then
    sudo apt-get install -y python3
fi
hash pip3 > /dev/null 2>&1
if [ $? -eq 1 ]
then
	sudo apt-get install -y python3-pip
fi
hash ipset > /dev/null 2>&1
if [ $? -eq 1 ]
then
	sudo apt-get install -y ipset
fi
sudo apt-get install net-tools xtables-addons-common fail2ban ufw miniupnpc -y
sudo pip3 install --upgrade requests python-iptables Django tcconfig bidict cherrypy gglsbl adblockparser IPy intervaltree bs4

sudo ufw enable
sudo ufw allow 22
sudo ufw allow 45679

# network command privilege
TC_BIN_PATH=`which tc`
IP_BIN_PATH=`which ip`
IPSET_BIN_PATH=`which ipset`
IPTABLES_BIN_PATH=`which xtables-multi` #/sbin/xtables-multi
sudo setcap cap_net_admin+ep ${TC_BIN_PATH}
sudo setcap cap_net_raw,cap_net_admin+ep ${IP_BIN_PATH}
sudo setcap cap_net_raw,cap_net_admin+ep ${IPSET_BIN_PATH}
sudo setcap cap_net_raw,cap_net_admin+ep ${IPTABLES_BIN_PATH}

# Try to set up UPnP
ip=`ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | grep -v '172.*.*.*'`
for port in 3000 80 443 9080 29444
do
#upnpc -a ${ip} ${port} ${port} TCP
sudo ufw allow ${port}
done
for port in 1194 25000
do
#upnpc -a ${ip} ${port} ${port} UDP
sudo ufw allow ${port}
done


# install java
#sudo apt-get update
#sudo apt install openjdk-8-jdk -y

# set up jenkins 
# TBD: send node info (IP and username) to controller
#mkdir -p .ssh
#touch .ssh/authorized_keys
#cat ${curdir}/../control/conf/master.pub >> .ssh/authorized_keys

# tstat
sudo apt-get install build-essential autoconf libtool libpcap-dev zlib1g libstat-lsmode-perl -y
if [ ! -d "tstat" ]
then
    wget http://tstat.polito.it/download/tstat-latest.tar.gz
    tar -xvf tstat-latest.tar.gz && mv tstat-?.?.? tstat && cd tstat
    ./autogen.sh
    ./configure --enable-libtstat --enable-zlib
    make
    cd ..
fi

# install docker
hash docker > /dev/null 2>&1
if [ $? -eq 1 ]
then
sudo apt-get remove docker docker-engine docker.io containerd runc
sudo apt-get update
sudo apt-get install apt-transport-https ca-certificates curl gnupg-agent software-properties-common -y
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo apt-key fingerprint 0EBFCD88
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# non-privilege set up
sudo groupadd docker
sudo usermod -aG docker $USER
if [[ "$arch" == "x86_64" ]]
then
newgrp docker << END
echo "$USER"
id
END
else 
newgrp docker
fi
fi

# pull the images
arch=`uname -m`
docker pull xiaoyunming/myst:${arch}
docker pull xiaoyunming/sentinel:${arch}
docker pull xiaoyunming/tachyon:${arch}
#docker pull letheanmovement/lethean-vpn:devel

cd ${curdir}
