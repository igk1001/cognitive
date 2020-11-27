import struct
import sys
import time
from bluepy.btle import UUID, Peripheral,DefaultDelegate
import threading
from queue import LifoQueue
from gpiozero.tones import Tone
from time import sleep
#import os
#os.environ['SDL_AUDIODRIVER'] = 'dsp'

from pygame import mixer

button_service_uuid = "00001812-0000-1000-8000-00805f9b34fb"
button_chararcteristics_uuid    = "00002a4d-0000-1000-8000-00805f9b34fb"

lock = threading.Lock()

generator_queue = LifoQueue()
ble_receiver_queue = LifoQueue()

results = []

#Admin APIs to manage a service
class Admin:
    pass

class Move:
    pass

#defines desired metronome sequence
# Ex. press left hand twice, right hand once,  left hand twice, etc
class Sequence:
    pass

#matches bits and tones
#t0, t1, t2
class Matcher(threading.Thread):
    def __init__(self):
        super(Matcher, self).__init__(name="Matcher")
        self.dd = 1

    def run(self):
        print ("creating thread {}".format (threading.currentThread().getName()))
        self.process()

    def process(self):
        while True:
            #print ("matching gqueue={}, blequeue={}".format (generator_queue.qsize(), ble_receiver_queue.qsize()))
            if ble_receiver_queue.empty == False:
                gitem = generator_queue.pop()
                ritem = ble_receiver_queue.pop()
                diff = gitem.ts-ritem.ts
                print ("difference {}, gqueue={}, blequeue={}".format (diff, generator_queue.qsize(), ble_receiver_queue.qsize()))
                sleep (0.1)


#generates sounds as per defined order
class BitGenerator(threading.Thread):
    class GItem:
        def __init__(self, ts):
            self.ts = ts

    def __init__(self, rate):
        super(BitGenerator, self).__init__(name="Generator")
        self.rate=rate
        mixer.init()
        self.sound = mixer.Sound('sounds/bottle_pop_2.wav')

    def run(self):
        print ("creating thread {}".format (threading.currentThread().getName()))
        self.generate()
    
    def generate(self):
        while True:
            item = self.GItem(int(time.time() * 1000))
            generator_queue.put(item)
            self.sound.play()
            #sleep (self.rate)

class BLEProcessor(threading.Thread):
    class BLEItem:
        def __init__(self, ts, device):
            self.ts = ts
            self.device = device

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
        #hack to suppress duplicate notifications
        self.count = 0
      
    #func is caled on notifications
    def handleNotification(self, cHandle, data):
        ts = int(time.time() * 1000)
        print (str(ts) + " Notification from Device:" + self.device + ", Handle: 0x" + format(cHandle,'02X') + " Count" + str(self.count))
        if self.count == 0:
            ble_receiver_queue.put(BLEProcessor.BLEItem(ts, self.device))
            self.count = self.count + 1
        else:
         if self.count > 0:
            self.count = 0
        

if len(sys.argv) != 2:
  print ("Fatal, must pass device address:", sys.argv[0], "<device address="">")
  quit()

devices = []
thread_list = []

for d in sys.argv[1].split(','):
    devices.append(d.strip())

matcher = Matcher()
matcher.setDaemon(True)
matcher.start()
thread_list.append(matcher)

generator = BitGenerator(1)
generator.setDaemon(True)
generator.start()
thread_list.append(generator)


for d in devices:
    thread = BLEProcessor(d)
    thread.setDaemon(True)
    thread_list.append (thread)
    thread.start()
    
for thread in thread_list:
    thread.join()


