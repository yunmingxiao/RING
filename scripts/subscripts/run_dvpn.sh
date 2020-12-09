#!/bin/bash -x

if [ $# -lt 1 ]; then
    echo "Usage: run_dvpn.sh dvpn_name";
    exit 0;
fi

arch=`uname -m`

if [ $1 = 'mysterium' ]; then
    DIR_MYST="$HOME/mysterium-node"
    port_ovpn_myst=25000
    port_ctrl_myst=4449
    eth_addr_myst=`cat config/eth_mysterium.conf`

    echo 'Run Mysterium'
    docker pull xiaoyunming/myst:${arch}
    docker run -d --rm \
    --cap-add NET_ADMIN -p ${port_ctrl_myst}:${port_ctrl_myst} -p ${port_ovpn_myst}:${port_ovpn_myst}/udp \
    --network=net-mysterium \
    --name mysterium \
    -v ${DIR_MYST}:/var/lib/mysterium-node \
    xiaoyunming/myst:${arch} \
    --experiment-natpunching=false \
    service --agreed-terms-and-conditions \
    --openvpn.port=${port_ovpn_myst}

    sleep 5 # waiting for myst to set up

    ip_myst=`cat ../conf/internal_myst.conf | cut -d'/' -f1`
    node_id=`sudo ls ${DIR_MYST}/keystore/ | grep UTC | cut -d'-' -f9`

    curl "http://${ip_myst}:4449/tequilapi/auth/login" \
    -H 'Accept: application/json, text/plain, */*' -H 'Content-Type: application/json;charset=UTF-8' \
    --data-binary '{"username":"myst","password":"mystberry"}' \
    -c tmp/cookie_myst.txt

elif [ $1 == 'sentinel' ]; then
    DIR_SENT="$HOME/sentinel"
    port_ovpn_sent=1194
    port_ctrl_sent=3000
    eth_addr_sent=`cat config/eth_sentinel.conf`
    
    echo 'Run Sentinel'
    mkdir -p ${DIR_SENT}
    python3 update_config.py eth ${eth_addr_sent}
    cp ../resources/sentinel/config.data ${DIR_SENT}/

    docker pull xiaoyunming/sentinel:${arch}
    docker run -d --rm \
    -p ${port_ctrl_sent}:${port_ctrl_sent} -p ${port_ovpn_sent}:${port_ovpn_sent}/udp \
    --network=net-sentinel \
    --name sentinel \
    --privileged \
    --mount type=bind,source=${DIR_SENT},target=/root/.sentinel \
    xiaoyunming/sentinel:${arch}

elif [ $1 == 'tachyon' ]; then
    DIR_TACH="$HOME/tachyon" 

    echo 'Run Tachyon'
    mkdir -p ${DIR_TACH}

    docker pull xiaoyunming/tachyon:${arch}
    docker run -d --rm \
    --cap-add=NET_ADMIN --device /dev/net/tun:/dev/net/tun --privileged \
    --network=net-tachyon --name tachyon \
    -p 9080:9080 -p 80:80 -p 443:443 -p 29444:29444 \
    -v ${DIR_TACH}:/usr/local/etc \
    xiaoyunming/tachyon:x86_64 \
    tyVpnServer run

    sleep 10
    cat ${DIR_TACH}/tachyonWatchdogPsk | awk '{printf "tynm://?ip=x.x.x.x&k=%s", $0}' # the key for controller

else
    echo 'Unsupported dvpn'
fi