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
    price_per_min=${3}

    echo 'Update Mysterium Address'
    ip_myst=`cat ../conf/internal_myst.conf | cut -d'/' -f1`
    node_id=`sudo ls ${DIR_MYST}/keystore/ | grep UTC | cut -d'-' -f9`

    curl "http://${ip_myst}:4449/tequilapi/auth/login" \
    -H 'Accept: application/json, text/plain, */*' -H 'Content-Type: application/json;charset=UTF-8' \
    --data-binary '{"username":"myst","password":"mystberry"}' \
    -c tmp/cookie_myst.txt

    curl "http://${ip_myst}:4449/tequilapi/config/user" \
    -H 'Accept: application/json, text/plain, */*' -H 'Content-Type: application/json;charset=UTF-8' \
    -H "Origin: http://${ip_myst}:4449" \
    -H "Referer: http://${ip_myst}:4449/" \
    -b tmp/cookie_myst.txt \
    --data-binary "{\"data\":{\"payment\":{\"price-gb\":${price},\"price-minute\":${price_per_min}},\"shaper\":{\"enabled\":false},\"openvpn\":{\"port\":25000,\"price-gb\":null,\"price-minute\":null},\"wireguard\":{\"price-gb\":null,\"price-minute\":null},\"access-policy\":null}}"

    service_id=`curl "http://${ip_myst}:4449/tequilapi/services" \
    -H 'Accept: application/json, text/plain, */*' -H 'Content-Type: application/json;charset=UTF-8' \
    -H "Origin: http://${ip_myst}:4449" \
    -H "Referer: http://${ip_myst}:4449/" \
    -b tmp/cookie_myst.txt \
    | xargs -0 python3 subscripts/simple_py.py`

    for sid in ${service_id}
    do 
        curl "http://${ip_myst}:4449/tequilapi/services/${sid}" \
        -X DELETE \
        -H 'Accept: application/json, text/plain, */*' -H 'Content-Type: application/json;charset=UTF-8' \
        -H "Origin: http://${ip_myst}:4449" \
        -H "Referer: http://${ip_myst}:4449/" \
        -b tmp/cookie_myst.txt
    done

    sleep 1

    for serv in 'openvpn' 'wireguard' 'noop'
    do
        curl "http://${ip_myst}:4449/tequilapi/services" \
        -X POST \
        -H 'Accept: application/json, text/plain, */*' -H 'Content-Type: application/json;charset=UTF-8' \
        -H "Origin: http://${ip_myst}:4449" \
        -H "Referer: http://${ip_myst}:4449/" \
        -b tmp/cookie_myst.txt \
        --data-binary "{\"provider_id\":\"0x${node_id}\", \"type\":\"${serv}\"}"
    done

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