import struct
import sys
import time
from bluepy.btle import UUID, Peripheral,DefaultDelegate
import threading
from gpiozero.tones import Tone
from time import sleep
from pygame import mixer

button_service_uuid = "00001812-0000-1000-8000-00805f9b34fb"
button_chararcteristics_uuid    = "00002a4d-0000-1000-8000-00805f9b34fb"

lock = threading.Lock()

#matches bits and tones
class Matcher:
    def __init__(self):
        self.dd = 1

#generates sounds as per defined order
class BitGenerator(threading.Thread):
    def __init__(self, rate):
        super(BitGenerator, self).__init__()
        self.rate=rate
        mixer.init()
        sound = mixer.Sound('sounds/bottle_pop_2.wav')

    def run(self):
        print ("creating thread {} for {}".format (threading.currentThread().getName(), self.device))
        self.generate()
    
    def generate(self):
        

class BLEProcessor(threading.Thread):
    def __init__(self, device):
        super(BLEProcessor, self).__init__(name=device)
        self.device=device

    def run(self):
        print ("creating thread {} for {}".format (threading.currentThread().getName(), self.device))
        self.subscribe()

    def subscribe(self):
        p = Peripheral(self.device)
        p.setDelegate( MyDelegate(self.device) )

        #Get ButtonService
        ButtonService=p.getServiceByUUID(button_service_uuid)

        print ("Connected to " + self.device)

        # Get The Button-Characteristics
        # for ch in ButtonService.getCharacteristics():
        #    print (ch.propertiesToString(), ch.uuid)

        ButtonC=ButtonService.getCharacteristics(button_chararcteristics_uuid)[0]
    
        #Get The handle tf the  Button-Characteristics
        hButtonC=ButtonC.getHandle()
        # Search and get Get The Button-Characteristics "property" (UUID-0x1124 Human Interface Device (HID)))
        #  wich is located in a handle in the range defined by the boundries of the ButtonService
        for desriptor in p.getDescriptors(hButtonC,0xFFFF):  # The handle range should be read from the services 
            #print ("descr", desriptor)
            # if (desriptor.uuid == 0x2902):                   #      but is not done due to a Bluez/BluePy bug :(     
            #print ("Button1 Client Characteristic Configuration found at handle 0x"+ format(desriptor.handle,"02X"))
            hButtonCCC=desriptor.handle
            p.writeCharacteristic(hButtonCCC, struct.pack('<bb', 0x01, 0x00))

        print ("Notification is turned on for " + self.device)

        while True:
            if p.waitForNotifications(1.0):
            # handleNotification() was called
                continue

class MyDelegate(DefaultDelegate):
    #Constructor (run once on startup)  
    def __init__(self, params):
        DefaultDelegate.__init__(self)
        self.device=params
      
    #func is caled on notifications
    def handleNotification(self, cHandle, data):
         #print ("Notification from Handle: 0x" + format(cHandle,'02X') + " Value: "+ format(ord(data[0])))
         print ( int(time.time() * 1000), " Notification from Device:" + self.device + ", Handle: 0x" + format(cHandle,'02X') + " Value: "+ str(data))
      

if len(sys.argv) != 2:
  print ("Fatal, must pass device address:", sys.argv[0], "<device address="">")
  quit()

devices = []
thread_list = []

for d in sys.argv[1].split(','):
    devices.append(d.strip())

for d in devices:
    thread = BLEProcessor(d)
    thread.setDaemon(True)
    thread_list.append (thread)
    thread.start()
    
for thread in thread_list:
    thread.join()


