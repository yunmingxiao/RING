#!/bin/bash -x

# parameters 
TIMEOUT=1200   # restart each N hours 

while true 
do 
    git stash
    git pull
    git stash pop
        
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


