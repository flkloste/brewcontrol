#!/usr/bin/python
import time
from random import randint

count = 0;

with open("test.csv", "w") as myfile:
	myfile.write("AAPL_x,AAPL_y\n")
	while 1:
	    myfile.write("%d,%d\n" % (count, count*randint(0,1000)))
	    count = count + 1
	    time.sleep(1)
	    myfile.flush()
