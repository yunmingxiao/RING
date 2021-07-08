# Usage

Make sure that the current user has the sudo access, and preferably the sudo does not requre password. 

Simply run the command 
```
./start.sh
```
and everything will be settled.

Open http://ip-of-the-machine:45679/index to manage the dVPNs. Note that you cannot access this URL if you're out of LAN. If you'd like to access outside the LAN, please make sure to configure the router to enable port 45679 accessible from WAN. But please be aware that others might be able to access it as well if they knew the IP address of your home and the port number.

If thigns do not work properly, it might be because of upnp. Then please make sure that the ports 1194, 3000 (for Sentinel), 25000 (for Mysterium), 80, 443, 9080, 29444 (for Tachyon) allow access from WAN. 
