# Usage

Make sure that the current user has the sudo access, and preferably the sudo does not requre password. 

If thigns do not work properly, it might be because of upnp. Then please make sure that the ports 1194, 3000 (for Sentinel), 25000 (for Mysterium), 80, 443, 9080, 29444 (for Tachyon) allow access from WAN. 

Simply run the command 
```
./start.sh
```
and everything will be settled.

Open http://ip-of-the-machine:45679/index to manage the dVPNs. 
