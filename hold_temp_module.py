#not /usr/bin/python
# -*- coding: utf-8 -*-

import re, time, sys, threading, datetime
import os
from subprocess import call

class MODE:
    HEAT = 1
    COOL = 2

def float2String(float_val):
    return str('%.2f' % float_val)

class InfoStats:
    def __init__(self, in_mode, in_soll_temp, in_ist_temp, in_is_running, in_power_status, in_hysterese, in_heat_cool_freq):
        self.mode = in_mode
        self.soll_temp = str(in_soll_temp)
        self.ist_temp = float2String(in_ist_temp)
        self.is_running = in_is_running
        self.power_status = in_power_status
        self.hysterese = str(in_hysterese)
        self.heat_cool_freq = float2String(in_heat_cool_freq)

class HoldTemp(threading.Thread):
    def __init__(self, in_mode, in_soll_temp, in_is_running, in_csv_lock):
        threading.Thread.__init__(self)
        
        #basepath = os.path.dirname(__file__)
        #self.csvFilePath = os.path.abspath(os.path.join(basepath, "test.csv"))
        #try:
        #    os.remove(self.csvFilePath)
        #except OSError:
        #    pass
        
        self.successiveStopHeatings = -1
        self.iterationCount = 0
        self.skipCount = 1
        self.csvEntries = list()
        self.lastValues = list()
        
                

        self.pilight_cmd_ON = ''
        self.pilight_cmd_OFF = ''
        self.hysterese = -1
        self.mode = in_mode
        if(in_mode == MODE.HEAT):
            self.pilight_cmd_ON = 'on'
            self.pilight_cmd_OFF = 'off'
            self.hysterese = 10
        elif (in_mode == MODE.COOL):
            self.pilight_cmd_ON = 'off'
            self.pilight_cmd_OFF = 'on'
            self.hysterese = 120
        else:
            raise ValueError("Error: No in_mode selected")


        self.power_status = 'off'
        self.heat_cool_count_list = list()
        self.heat_cool_count_lock = threading.Lock()
        self.soll_temp = in_soll_temp
        self.soll_temp_lock = threading.Lock()
        self.ist_temp = 0
        self.ist_temp_lock = threading.Lock()
        self.is_running = in_is_running
        self.is_running_lock = threading.Lock()
        self.csv_lock = in_csv_lock
        self._stop = threading.Event()
        self.hysterese_lock = threading.Lock()

        self.pilightSystemCall('off')   

        #with self.csv_lock:
        #    with open("test.csv", "w") as csvFile:
        #        csvFile.truncate()
        #        csvFile.write("Zeit,Ist,Soll\n")

    # make thread stoppable
    def stop(self):
        # remove csv
        #try:
        #    os.remove(self.csvFilePath)
        #except OSError:
        #    pass
        self._stop.set()
        
    def pilightSystemCall(self, status):
        if (status not in ['on', 'off']):
            print "Invalid status. Must be 'on' or 'off'"
            return
        call(['pilight-control', '-d', 'HiFi', '-s', status, '-S=127.0.0.1', '-P', '5002'])
        self.power_status = status

    def getHeatCoolFrequency(self):
        with self.heat_cool_count_lock:
            return len([x for x in self.heat_cool_count_list if x == 'on']) / float(len(self.heat_cool_count_list))

    def isStopped(self):
        return self._stop.isSet()

    def getInfoStats(self):                
        result = InfoStats(self.mode, self.getSollTemp(), self.getIstTemp(), self.getIsRunning(), self.power_status, self.getHysterese(), self.getHeatCoolFrequency())
        return result

    def getSollTemp(self):
        with self.soll_temp_lock:
            return int(self.soll_temp)

    def setHysterese(self, in_hysterse):
        with self.hysterese_lock:
            self.hysterese = in_hysterse

    def getHysterese(self):
        with self.hysterese_lock:
            return self.hysterese

    def setSollTemp(self, in_new_soll_temp):
        with self.soll_temp_lock:
            self.soll_temp = int(in_new_soll_temp)
        
    def getIstTemp(self):
        return self.getTemp()

    def getIsRunning(self):
        with self.is_running_lock:
            return self.is_running

    def startControl(self):
        with self.is_running_lock:
            self.is_running = 1

    def stopControl(self):
        self.pilightSystemCall('off')
        with self.is_running_lock:
            self.is_running = 0

    # function: read and parse sensor data file
    def read_sensor(self):
        #path = "/sys/bus/w1/devices/28-04168415c8ff/w1_slave"
        path = "/sys/bus/w1/devices/28-021481420bff/w1_slave"
        value = "U"
        try:
            f = open(path, "r")
            line = f.readline()
            if re.match(r"([0-9a-f]{2} ){9}: crc=[0-9a-f]{2} YES", line):
                line = f.readline()
                m = re.match(r"([0-9a-f]{2} ){9}t=([+-]?[0-9]+)", line)
                if m:
                    value = float(m.group(2)) / 1000.0
            f.close()
        except (IOError), e:
            print time.strftime("%x %X"), "Error reading", path, ": ", e
        return value

    def getTemp(self):
        with self.ist_temp_lock:
            result = 0
            try:
                result = self.read_sensor()
                while(result == 85.0 or result == "U"):
                    time.sleep(1)
                    result = self.read_sensor()
            except:
                # try again
                time.sleep(1)
                return self.getTemp()
                
            # temp_des;temp_akt;isHeating
            # self.ist_temp_queue.put("%s;%s;%s"%(self.temp_des, result, self.isHeating))
            return result

    def storeValue(self, value):
        #speicher nur neue Werte
        #if len(self.lastValues) == 0 or value != self.lastValues[-1]:
        #   if len(self.lastValues) > 2:
        #       self.lastValues.pop(0)
        self.lastValues.append(value)

    def isSinking(self):
        reversed_list = self.lastValues[::-1]
        count = 0
        last_val = -1000.0
        
        for val in reversed_list:
            if val >= last_val:
                count += 1
                last_val = val
            else:
                break

        if count > 1 and reversed_list[count-1] - reversed_list[0] > 0.3:
            self.lastValues = []
            return True

        return False

    def isRising(self):
        reversed_list = self.lastValues[::-1]
        count = 0
        last_val = 1000.0

        for val in reversed_list:
            if val <= last_val:
                count += 1
                last_val = val
            else:
                break

        if count > 1 and reversed_list[0] - reversed_list[count-1] > 0.3:
            self.lastValues = []
            return True

        return False

    def startHeating(self):
        if(self.getIsRunning() == 1):
            if(self.power_status == self.pilight_cmd_OFF):
                self.pilightSystemCall(self.pilight_cmd_ON)
                self.successiveStopHeatings = -1

    def stopHeating(self):
        if(self.getIsRunning() == 1):
        
            self.successiveStopHeatings += 1
			
            if(self.power_status == self.pilight_cmd_ON):
                if self.mode == MODE.COOL and self.successiveStopHeatings % 6 != 0:
                    return 0
                self.pilightSystemCall(self.pilight_cmd_OFF)

            # turn fridge off after one time period of cooling
            elif self.mode == MODE.COOL and (self.getSollTemp() < self.getIstTemp() < (self.getSollTemp() + 0.3)):
                    self.pilightSystemCall(self.pilight_cmd_ON)
                    

    # attach entry to list whereby list is automatically shortened when exceeding size 4000
    def attachToCsvEntryList(self, entry):
        with self.csv_lock:
            self.iterationCount = self.iterationCount + 1
            if len(self.csvEntries) < 4000:
                if self.iterationCount % self.skipCount == 0:
                    self.csvEntries.append(entry)
            else:
                self.skipCount = self.skipCount * 2  # adjust intervals between values for future values
                del self.csvEntries[1::2] # delete every second item

                
    #def writeCsv(self):
    #    #print self.csvFilePath
    #    with self.csv_lock:
    #        with open(self.csvFilePath, "w") as csvFile:
    #            csvFile.truncate()
    #            csvFile.write("Zeit,Ist,Soll\n")
    #           for line in self.csvEntries:
    #                csvFile.write(line)
                    
                    
    def getCsv(self):
        with self.csv_lock:
            return self.csvEntries


    # main routine
    def run(self):

        if not isInt(self.getSollTemp()):
            raise ValueError("Error: invalid target temperature (not an int)")

        if self.getSollTemp() < 0 or self.getSollTemp() > 100:
            raise ValueError("Error: invalid target temperature (must be between 0 and 100)")

        try:
            #log = open('test.csv', 'w')
            #log.truncate()
            #log.write("Zeit,Ist,Soll\n")


            while(not self.isStopped()):

                istTemp = self.getTemp()
                self.storeValue(istTemp)
                sollTemp = self.getSollTemp()

                # temp ist drueber
                if istTemp > sollTemp:

                    # temp faellt und ist kurz vorm ziel
                    if self.isSinking() and istTemp < sollTemp+1:
                        self.startHeating()
                    else:
                        self.stopHeating()

                # temp ist drunter
                elif istTemp < sollTemp:

                    #temp steigt und ist kurz vorm ziel
                    if (self.mode != MODE.COOL) and self.isRising() and istTemp > sollTemp-1:
                        self.stopHeating()
                    else:
                        self.startHeating()

                with self.heat_cool_count_lock:
                    if len(self.heat_cool_count_list) >= 100:
                        self.heat_cool_count_list.pop(0)
                    self.heat_cool_count_list.append(self.power_status)

                if(self.is_running == 1):
                    ## log.write('%s,%s,%s\n' % ('{:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now()), ('%.2f' % istTemp), sollTemp))
                    ##  log.flush()
                    csvEntry = '%s,%s,%s,%s\n' % ('{:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now()), ('%.2f' % istTemp), sollTemp, self.getHeatCoolFrequency())
                    self.attachToCsvEntryList(csvEntry)
                    #self.writeCsv()

                time.sleep(self.getHysterese())

        except:
            print 'Good-bye'
            #print 'aktuelle temp: %s; gewuenschte temp: %s, heizt: %s' % (istTemp, sollTemp, self.power_status)
            print sys.exc_info()
            self.stopControl()

def isInt(value):
    try:
        int(value)
        return True
    except:
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print 'Usage: python hold_temp_module.py <temperature>'
        sys.exit()

    if not isInt(sys.argv[1]):
        print 'not a number :('
        sys.exit()

    temp_des = int(sys.argv[1])
    if temp_des < 0 or temp_des > 100:
        print 'ungueltige temperatur!'
        sys.exit()

    ht = HoldTemp(MODE.HEAT, 50, 1)
    ht.start()
