#!/bin/bash -x

docker network create --driver=bridge --opt com.docker.network.bridge.name=net-mysterium net-mysterium
docker network create --driver=bridge --opt com.docker.network.bridge.name=net-sentinel net-sentinel
docker network create --driver=bridge --opt com.docker.network.bridge.name=net-tachyon net-tachyon

ip addr | grep "net-mysterium" | grep "inet" | awk '{printf "%s", $2}' > ../conf/internal_myst.conf
ip addr | grep "net-sentinel" | grep "inet" | awk '{printf "%s", $2}' > ../conf/internal_sentinel.conf
ip addr | grep "net-tachyon" | grep "inet" | awk '{printf "%s", $2}' > ../conf/internal_tachyon.conf
