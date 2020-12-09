#!/bin/bash -x

for pid in `ps aux | grep "tstat" | awk '{print $2}'`; do  sudo kill -9 $pid ; done