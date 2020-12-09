#!/bin/bash -x

if [ "$#" != 1 ]
then
    echo "Usage: new_dir.sh path"
    exit 1
fi

mkdir -p "$1"/jsons "$1"/filters "$1"/figs 
mkdir -p "$1"/output/myst "$1"/output/sentinel "$1"/output/tachyon

curl https://easylist.to/easylist/easylist.txt > "$1"/filters/easylist.txt
curl https://easylist.to/easylist/easyprivacy.txt > "$1"/filters/easyprivacy.txt
curl https://iplists.firehol.org/files/firehol_level1.netset > "$1"/filters/firehol_level1.netset

cp sample/filters/* "$1"/filters

python3 update_gsb.py
cp gsb_v4.db "$1"/filters/gsb_v4.db