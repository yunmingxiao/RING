#!/bin/bash -x

source download.sh

today=`date | awk '{printf "%s%s%s", $6, $2, $3}'`
source new_dir.sh "${today}"
sudo mv ../output/myst/* "${today}"/output/myst
sudo mv ../output/sentinel/* "${today}"/output/sentinel
sudo mv ../output/tachyon/* "${today}"/output/tachyon

sed -i -e "s/DVPN_DIR = '.*'/DVPN_DIR = '${today}'/" Constants.py
sed -i -e "s/TARGET_DIR = '.*'/TARGET_DIR = '${today}'/" Constants.py

python3 parse_tstat_tree.py requests
python3 get_labels.py
python3 parse_tstat_tree.py conns
python3 upload.py