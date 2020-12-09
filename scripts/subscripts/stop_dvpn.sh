#!/bin/bash -x

if [ $# -lt 1 ]; then
    echo "Usage: stop_dvpn.sh dvpn_name";
    exit 0;
fi
docker stop $1