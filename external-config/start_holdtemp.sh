#!/bin/sh
#sleep 20
#sudo service pilight restart
sudo iptables -A INPUT -s 127.0.01 -j ACCEPT
#sudo /usr/local/sbin/pilight-daemon > /home/pi/pilightdeamon.log

sleep 5
#sudo python /home/pi/holdtemp/bt_controller.py
sudo noip2
sudo python -u /home/pi/python-server-brew-control/pythonserver.py &> /home/pi/pythonserver_error.log

