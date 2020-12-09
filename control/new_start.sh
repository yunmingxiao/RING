#!/bin/bash -x
# please run this script at parent directory

cur_dir=`pwd`
cd scripts
source install.sh
source create_net.sh
source record.sh

cd ringweb
source restart.sh &
cd ${cur_dir}

source control/result_processing.sh &

source control/git_update.sh >> control/github.log 2>&1 &