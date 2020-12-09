#!/bin/bash -x

# Settings
arch=`uname -m`

DIR_MYST="$HOME/mysterium-node"
port_ovpn_myst=25000
port_ctrl_myst=4449
pw_myst='yunming'
eth_addr_myst=`cat config/eth_mysterium.conf`

DIR_SENT="$HOME/sentinel"
port_ovpn_sent=1194
port_ctrl_sent=3000
eth_addr_sent=`cat config/eth_sentinel.conf`

DIR_TACH="$HOME/tachyon"

DIR_LTHN="$HOME/lethean"
pw_lthn='dvpn_test'
port_ovpn_lthn=8280

# Mysterium
echo 'Run Mysterium'
docker run -d --rm \
 --cap-add NET_ADMIN -p ${port_ctrl_myst}:${port_ctrl_myst} -p ${port_ovpn_myst}:${port_ovpn_myst}/udp \
 --network=net-mysterium \
 --name mysterium \
 -v ${DIR_MYST}:/var/lib/mysterium-node \
 xiaoyunming/myst:${arch} \
 --experiment-natpunching=false \
 service --agreed-terms-and-conditions \
 --openvpn.port=${port_ovpn_myst} \
 --identity.passphrase=${pw_myst}

sleep 5 # waiting for myst to set up

ip_myst=`cat ../conf/internal_myst.conf | cut -d'/' -f1`
node_id=`sudo ls ${DIR_MYST}/keystore/ | grep UTC | cut -d'-' -f9`

curl "http://${ip_myst}:4449/tequilapi/auth/login" \
 -H 'Accept: application/json, text/plain, */*' -H 'Content-Type: application/json;charset=UTF-8' \
 --data-binary '{"username":"myst","password":"mystberry"}' \
 -c tmp/cookie_myst.txt

curl "http://${ip_myst}:4449/tequilapi/auth/password" \
 -X 'PUT' \
 -H 'Accept: application/json, text/plain, */*' -H 'Content-Type: application/json;charset=UTF-8' \
 -b tmp/cookie_myst.txt \
 --data-binary '{"username":"myst","old_password":"mystberry","new_password":"yunming"}'

curl "http://${ip_myst}:4449/tequilapi/identities/0x${node_id}/payout" \
 -X 'PUT' \
 -H 'Accept: application/json, text/plain, */*' -H 'Content-Type: application/json;charset=UTF-8' \
 -H "Origin: http://${ip_myst}:4449" \
 -H "Referer: http://${ip_myst}:4449/" \
 -b tmp/cookie_myst.txt \
 --data-binary "{\"eth_address\":\"${eth_addr_myst}\"}"

curl "http://${ip_myst}:4449/tequilapi/config/user" \
 -H 'Accept: application/json, text/plain, */*' -H 'Content-Type: application/json;charset=UTF-8' \
 -H "Origin: http://${ip_myst}:4449" \
 -H "Referer: http://${ip_myst}:4449/" \
 -b tmp/cookie_myst.txt \
 --data-binary '{"data":{"openvpn":{"port":25000,"price-gb":null,"price-minute":null},"payment":{},"shaper":{"enabled":false},"wireguard":{"price-gb":null,"price-minute":null},"access-policy":null}}'
#"access-policy": "mysterium"

# Sentinel
echo 'Run Sentinel'
mkdir -p ${DIR_SENT}
python3 update_config.py eth ${eth_addr_sent}
cp ../resources/sentinel/config.data ${DIR_SENT}/

docker run -d --rm \
 -p ${port_ctrl_sent}:${port_ctrl_sent} -p ${port_ovpn_sent}:${port_ovpn_sent}/udp \
 --network=net-sentinel \
 --name sentinel \
 --privileged \
 --mount type=bind,source=${DIR_SENT},target=/root/.sentinel \
 xiaoyunming/sentinel:${arch}
#docker run -d --name sentinel --privileged --mount type=bind,source="$HOME/sentinel,target=/root/.sentinel -p 3000:3000 -p 1194:1194/udp sentinelofficial/sentinel-vpn-node --network=net-sentinel

# Tychyon
echo 'Run Tachyon'
mkdir -p ${DIR_TACH}
docker run -d --rm \
 --cap-add=NET_ADMIN --device /dev/net/tun:/dev/net/tun --privileged \
 --network=net-tachyon --name tachyon \
 -p 9080:9080 -p 80:80 -p 443:443 -p 29444:29444 \
 -v ${DIR_TACH}:/usr/local/etc \
 xiaoyunming/tachyon:x86_64 \
 tyVpnServer run

sleep 10
cat ${DIR_TACH}/tachyonWatchdogPsk | awk '{printf "tynm://?ip=x.x.x.x&k=%s", $0}' # the key for controller

# Lethean
#echo 'Run Lethean'
#mkdir -p ${DIR_LTHN}/lthn ${DIR_LTHN}/data/ha ${DIR_LTHN}/data/log ${DIR_LTHN}/data/ovpn ${DIR_LTHN}/data/run

#docker run -it --rm \
# -e PORT=${port_ovpn_lthn} -e WALLET_FILE="vpn" -e WALLET_PASSWORD="${pw_lthn}" -e WALLET_RPC_PASSWORD="${pw_lthn}" \
# -p ${port_ovpn_lthn}:${port_ovpn_lthn} \
# --network=net-lethean \
# --mount type=bind,source=${DIR_LTHN}/lthn,target=/etc/lthn \
# --mount type=bind,source=${DIR_LTHN}/data,target=/var/lib/lthn \
# --mount type=bind,source=/dev/log,target=/dev/log \
# --name lethean \
# letheanmovement/lethean-vpn:devel easy-deploy

#docker run -d --rm \
# -e PORT=${port_ovpn_lthn} -e WALLET_FILE="vpn" -e WALLET_PASSWORD="${pw_lthn}" -e WALLET_RPC_PASSWORD="${pw_lthn}" \
# -p ${port_ovpn_lthn}:${port_ovpn_lthn} \
# --network=net-lethean \
# --mount type=bind,source=${DIR_LTHN}/lthn,target=/etc/lthn \
# --mount type=bind,source=${DIR_LTHN}/data,target=/var/lib/lthn \
# --mount type=bind,source=/dev/log,target=/dev/log \
# --name lethean \
# letheanmovement/lethean-vpn:devel run

# docker run -d \
#  -e WALLET_FILE="vpn" -e WALLET_PASSWORD=${pw_leth} -e WALLET_RPC_PASSWORD=${pw_leth} -e PORT=${port_ovpn_leth} \
#  --network=net-lethean \
#  -p ${port_ovpn_leth}:${port_ovpn_leth} \
#  --rm --name lethean \
#  --mount type=bind,source=${DIR_LETH}/etc,target=/opt/lthn/etc --mount type=bind,source=${DIR_LETH}/dev/log,target=/dev/log \
#  limosek/lethean-vpn:devel easy-deploy

# docker run -d \
#  -e WALLET_FILE="vpn" -e WALLET_PASSWORD=${pw_leth} -e WALLET_RPC_PASSWORD=${pw_leth} -e PORT=${port_ovpn_leth} \
#  -p ${port_ovpn_leth}:${port_ovpn_leth} \
#  --rm --name lethean \
#  --mount type=bind,source=${DIR_LETH}/etc,target=/opt/lthn/etc --mount type=bind,source=${DIR_LETH}/dev/log,target=/dev/log \
#  limosek/lethean-vpn:devel

#docker run -d --rm -p 29443:29443 --privileged --cap-add=NET_ADMIN --device=/dev/net/tun --name tachyon-server --network=net-tachyon -v $HOME/tachyon:/usr/local/etc tachyon-server-on-docker:1
#docker run -it --rm -p 29444:29444 --privileged --cap-add=NET_ADMIN --device=/dev/net/tun --name tachyon-server --network=net-tachyon -v $HOME/tachyon:/usr/local/etc tachyon-server-on-docker:1


#docker run -it --rm --cap-add=NET_ADMIN --name substratum -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix -v "$(pwd)"/../../target/release:/node substratum:test
#docker run -it --rm --cap-add=NET_ADMIN --name substratum -v "$(pwd)"/../../target/release:/node substratum:test