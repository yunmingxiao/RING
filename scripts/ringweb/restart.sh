#!/bin/bash

# parameters 
TIMEOUT=604800   # restart each N hours 

# keep running until needed
if [ ! -f ".should_run" ]
then 
    echo "Something is wrong. File <<.should_run>> is missing"
    exit -1 
fi 
mkdir -p logs
is_running=`cat ".should_run"`
old_pid=-1
num_restart=0
echo "Restart"
while [ $is_running == "true" ] 
do 
    # derive a new log per day (append or create)
    suffix=`date +%m-%d-%y`"-"$num_restart
    log_file="./logs/log-web-app-"$suffix".txt"

    # check if a pending process is running
	pid=`ps aux | grep "web-app" | grep "python3" | awk '{print $2}'`
    if [ ! -z $pid ]
	then
        echo "Stopping pid: $pid (should be matching old_pid: $old_pid)"
		kill -9 $pid 
	fi 
	
    # start web-app 
    echo "Starting web app"
    (python3 web-app.py >> $log_file 2>&1 &)
    sleep 5 
    pid=`ps aux | grep "web-app" | grep "python3" | awk '{print $2}'`
    echo "Started new web-app instance. PID: $pid LOGFILE: $log_file"
        
    # monitor web-app did not crash or a timeout has passed
    t_start=`date +%s`
    t_passed=0
    while [ $t_passed -lt $TIMEOUT ]
    do 
        # check if active 
        pid=`ps aux | grep "web-app" | grep "python3" | awk '{print $2}'`
    	if [ -z $pid ]
        then
            echo "WARNING. It seems web-app died? PID $old_pid not found. RESTART"
            break 
        fi  
        old_pid=$pid

        # check for OSError
        cat $log_file | grep "OSError" > /dev/null
        if [ $? -eq 0 ]
        then 
           echo "WARNING. Detected OSError. RESTART"
            break 
        fi 

        # check if we should interrupt 
        is_running=`cat .should_run`
        if [ $is_running != "true" ]
        then
            echo "WARNING. Script $0 was interrupted via file <<.should_run>>"
            break
        fi 
        
        # rate control 
        sleep 5
        t_now=`date +%s`    
        let "t_passed = t_now - t_start"
    done
	# make sure each restart has a unique id 
	let "num_restart++"
done
