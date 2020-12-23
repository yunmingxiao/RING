#!/bin/bash -x

# parameters 
TIMEOUT=1200   # test regularly 

while true 
do 
    for port in 3000 80 443 9080 29444
    do
        upnpc -l | grep ":${port}" || upnpc -a ${ip} ${port} ${port} TCP
    done
    for port in 1194 25000
    do
        upnpc -l | grep ":${port}" || upnpc -a ${ip} ${port} ${port} UDP
    done
    
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


