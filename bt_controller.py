'''
Created on 31.10.2016

@author: florian
'''

from bluetooth import *
import time
import hold_temp_module as htmp
import Queue, re
import select

def initServer():
    server_sock=BluetoothSocket( RFCOMM )
    server_sock.bind(("",PORT_ANY))
    server_sock.listen(1)

    uuid = "00001101-0000-1000-8000-00805F9B34FB"

    advertise_service(server_sock, "Echo Server",
        service_id = uuid,
        service_classes = [ uuid, SERIAL_PORT_CLASS ],
        profiles = [ SERIAL_PORT_PROFILE ]
    )
    return server_sock

def getClientConnection(server_sock):
    print "Waiting for connection"
    client_sock, client_info = server_sock.accept()
    print "accepted connection from ", client_info
    return client_sock

def manageConnection(socket):
    
    try:
        # verbindung aktiv
        lastData = 0
        queue_temp = Queue.Queue()
        ht = htmp.HoldTemp(0, queue_temp)
        ht.daemon = True
        ht.start()
        
        while True:
            
            r,w,e = select.select([socket],[],[],0.5)
            
            for s in r:
                data = s.recv(1024)
                print data
                if lastData != data:
                    lastData = data
                    
                    value = int(re.findall(r'\d+', data)[0])
                    
                    ht.stop()
                    time.sleep(2)
                    ht = htmp.HoldTemp(value, queue_temp)
                    ht.daemon = True
                    ht.start()
                    print "received [%s]" % data
                    
            print 'busy'
            
            #data = socket.recv(1024)
            #if len(data) == 0: break
            # neue temperatur received
              
            if not queue_temp.empty():
                temp = queue_temp.get()
                socket.send("%s\n" % temp)
                #socket.send("Echo from Pi: [des_temp: %s]\n" % temp) 
                 
    except IOError:
        print 'Verbindung getrennt'
        ht.stop()
        pass


while  True:
    server=initServer()
    client=getClientConnection(server)
    manageConnection(client)
    client.close()
    server.close()
print "terminating..."
