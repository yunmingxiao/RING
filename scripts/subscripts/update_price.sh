#!/bin/bash -x

if [ $# -lt 1 ]; then
    echo "Usage: update_eth.sh dvpn_name address";
    exit 0;
fi

arch=`uname -m`
price=${2}

if [ $1 = 'mysterium' ]; then
    DIR_MYST="$HOME/mysterium-node"
    port_ovpn_myst=25000
    port_ctrl_myst=4449

    echo 'Update Mysterium Address'
    ip_myst=`cat ../conf/internal_myst.conf | cut -d'/' -f1`
    node_id=`sudo ls ${DIR_MYST}/keystore/ | grep UTC | cut -d'-' -f9`

    curl "http://${ip_myst}:4449/tequilapi/config/user" \
    -H 'Accept: application/json, text/plain, */*' -H 'Content-Type: application/json;charset=UTF-8' \
    -H "Origin: http://${ip_myst}:4449" \
    -H "Referer: http://${ip_myst}:4449/" \
    -b tmp/cookie_myst.txt \
    --data-binary "{\"data\":{\"openvpn\":{\"port\":25000,\"price-gb\":${price},\"price-minute\":null},\"payment\":{},\"shaper\":{\"enabled\":false},\"wireguard\":{\"price-gb\":null,\"price-minute\":null},\"access-policy\":null}}"


elif [ $1 == 'sentinel' ]; then
    DIR_SENT="$HOME/sentinel"
    port_ovpn_sent=1194
    port_ctrl_sent=3000
    
    echo 'Update Sentinel Address'
    python3 update_config.py price ${price}
    cp ../resources/sentinel/config.data ${DIR_SENT}/

elif [ $1 == 'tachyon' ]; then
    echo 'Unsupported Action'
else
    echo 'Unsupported dVPN'
fi