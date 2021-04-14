#!/bin/bash -x
# please run this script at parent directory

cur_dir=`pwd`

pkill -9 tstat
kill -9 $(pgrep -x new_start.sh | grep -v ^$$$)

source control/git_update.sh >> control/github.log 2>&1 &
sleep 3

cd scripts
source install.sh
source create_net.sh
source stop_record.sh
#source record.sh

cd ringweb
source restart.sh &
cd ${cur_dir}

source control/upnp.sh 2>&1 &
source control/result_processing.sh &
