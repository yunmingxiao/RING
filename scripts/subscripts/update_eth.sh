#!/bin/bash -x

if [ $# -lt 1 ]; then
    echo "Usage: update_eth.sh dvpn_name address";
    exit 0;
fi

arch=`uname -m`
eth_addr=${2}

if [ $1 = 'mysterium' ]; then
    DIR_MYST="$HOME/mysterium-node"
    port_ovpn_myst=25000
    port_ctrl_myst=4449
    
    echo 'Update Mysterium Address'
    echo "${eth_addr}" > config/eth_mysterium.conf
    ip_myst=`cat ../conf/internal_myst.conf | cut -d'/' -f1`
    node_id=`sudo ls ${DIR_MYST}/keystore/ | grep UTC | cut -d'-' -f9`

    curl "http://${ip_myst}:4449/tequilapi/auth/login" \
    -H 'Accept: application/json, text/plain, */*' -H 'Content-Type: application/json;charset=UTF-8' \
    --data-binary '{"username":"myst","password":"mystberry"}' \
    -c tmp/cookie_myst.txt

    curl "http://${ip_myst}:4449/tequilapi/identities/0x${node_id}/payout" \
    -X 'PUT' \
    -H 'Accept: application/json, text/plain, */*' -H 'Content-Type: application/json;charset=UTF-8' \
    -H "Origin: http://${ip_myst}:4449" \
    -H "Referer: http://${ip_myst}:4449/" \
    -b tmp/cookie_myst.txt \
    --data-binary "{\"eth_address\":\"${eth_addr}\"}"

elif [ $1 == 'sentinel' ]; then
    DIR_SENT="$HOME/sentinel"
    port_ovpn_sent=1194
    port_ctrl_sent=3000
    
    echo 'Update Sentinel Address'
    echo "${eth_addr}" > eth_sentinel.conf
    python3 update_config.py eth ${eth_addr}
    cp ../resources/sentinel/config.data ${DIR_SENT}/

elif [ $1 == 'tachyon' ]; then
    echo 'Unsupported Action'
else
    echo 'Unsupported dVPN'
fi