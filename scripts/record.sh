#!/bin/bash -x

dir="$(dirname "${PWD}")"

mkdir -p ${dir}/output/myst
(sudo $HOME/tstat/tstat/tstat -l -N ${dir}/conf/internal_myst.conf -T ${dir}/conf/runtime.conf -s ${dir}/output/myst/ -i net-mysterium > ${dir}/output/myst/log.txt 2>&1 &)

mkdir -p ${dir}/output/sentinel
(sudo $HOME/tstat/tstat/tstat -l -N ${dir}/conf/internal_sentinel.conf -T ${dir}/conf/runtime.conf -s ${dir}/output/sentinel/ -i net-sentinel > ${dir}/output/sentinel/log.txt 2>&1 &)

mkdir -p ${dir}/output/lethean
(sudo $HOME/tstat/tstat/tstat -l -N ${dir}/conf/internal_lethean.conf -T ${dir}/conf/runtime.conf -s ${dir}/output/lethean/ -i net-lethean > ${dir}/output/lethean/log.txt 2>&1 &)

mkdir -p ${dir}/output/tachyon
(sudo $HOME/tstat/tstat/tstat -l -N ${dir}/conf/internal_tachyon.conf -T ${dir}/conf/runtime.conf -s ${dir}/output/tachyon/ -i net-tachyon > ${dir}/output/tachyon/log.txt 2>&1 &)

#sudo tc qdisc add dev docker0 root tbf rate 1mbit buffer 1600 limit 3000
#tc qdisc show
#sudo tc qdisc del dev docker0 root
