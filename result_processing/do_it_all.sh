#!/bin/bash -x

source download.sh

ls -d */ | grep -v '__pycache__\|sample\|test' | awk '{printf "%soutput/\n",$1}' | sudo xargs rm -r

today=`date | awk '{printf "%s%s%s", $6, $2, $3}'`
source new_dir.sh "${today}"
sudo mv ../output/myst/* "${today}"/output/myst
sudo mv ../output/sentinel/* "${today}"/output/sentinel
sudo mv ../output/tachyon/* "${today}"/output/tachyon

sed -i -e "s/DVPN_DIR = '.*'/DVPN_DIR = '${today}'/" Constants.py
sed -i -e "s/TARGET_DIR = '.*'/TARGET_DIR = '${today}'/" Constants.py

#python3 parse_tstat_tree.py requests >> process.log
#python3 get_labels.py >> process.log
#python3 parse_tstat_tree.py conns >> process.log
python3 upload.py >> process.log
