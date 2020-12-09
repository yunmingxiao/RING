#!/bin/bash -x
# please run this script at parent directory

cur_dir=`pwd`
cd result_processing
source restart.sh >> process.log 2>&1 &
cd ${cur_dir}