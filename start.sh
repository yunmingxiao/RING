#!/bin/bash
# please run this script at parent directory

cur_dir=`pwd`

sudo pkill -9 tstat
sudo kill -9 $(pgrep -x start.sh | grep -v ^$$$)

source control/git_update.sh >> control/github.log 2>&1 &
sleep 3

cd scripts
source install.sh
source create_net.sh
source stop_record.sh
#source record.sh

cd ringweb
source restart.sh > start.log &
cd ${cur_dir}

source control/upnp.sh 2>&1 &
source control/result_processing.sh &
echo "RING started successfully!"
