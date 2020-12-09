#!/bin/bash -x

# parameters 
TIMEOUT=259200 #86400 #604800   # restart each week

while true 
do 
    source do_it_all.sh
        
    # monitor web-app did not crash or a timeout has passed
    t_start=`date +%s`
    t_passed=0
    while [ $t_passed -lt $TIMEOUT ]
    do  
        # rate control 
        sleep 600
        t_now=`date +%s`    
        let "t_passed = t_now - t_start"
    done
done
