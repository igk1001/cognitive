import struct
import sys
import time
from bluepy.btle import UUID, Peripheral,DefaultDelegate
import threading
import queue
from time import sleep
from datetime import datetime
from utils.note import Note
import argparse
import json
import urllib.parse
import requests
import random

from flask import Flask, Response, jsonify, render_template
from flask_classful import FlaskView, route

import logging

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.WARNING)

app = Flask(__name__)


# https://www.alibaba.com/product-detail/Bluetooth-Lighting-Dance-mat-Light-Up_1600146743226.html?spm=a2700.pc_countrysearch.main07.59.76656181zbKfbL

#TODO: async BLE library
#https://github.com/hbldh/bleak

button_service_uuid = "00001812-0000-1000-8000-00805f9b34fb"
button_chararcteristics_uuid    = "00002a4d-0000-1000-8000-00805f9b34fb"

HZ = 300

glock = threading.Lock()
results_lock = threading.Lock()

generator_queue = []
ble_receiver_queue = []
results = queue.Queue()
devices = []
thread_list = []


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
#TODO: may be i need to separate generation and the sound?

class Matcher(threading.Thread):
    def __init__(self):
        super(Matcher, self).__init__(name="Matcher")
        self.dd = 1

    def run(self):
        print ("creating thread {}".format (threading.currentThread().getName()))
        self.process()

    def process(self):
        while True:
            with ble_lock:
                if len(ble_receiver_queue) > 0:
                    ritem = ble_receiver_queue.pop()
                    with glock:
                        if len(generator_queue) > 0:
                            gitem = generator_queue.pop()
                            diff = gitem.ts-ritem.ts
                        else:
                            diff = 9999999

                    print ("difference {}, gqueue={}, blequeue={}".format (diff/1000000, len(generator_queue), len(ble_receiver_queue)))
                    results 
            #else:
            #    print ("matching gqueue={}, blequeue={}".format (generator_queue.qsize(), ble_receiver_queue.qsize()))
        sleep(0.5)


#generates sounds as per defined order
#TODO: can we use generators to produce values on a fly:
#TODO: explore futures - schedule a task that cancelled if event didnt happen in time 


class BitGenerator(threading.Thread):
    class GItem:
        def __init__(self, ts):
            self.ts = ts

    def __init__(self, rate):
        super(BitGenerator, self).__init__(name="Generator")
        self.rate=rate
        self.beep = self.rate*0.33
        self.pause = self.rate-self.beep
        

    def run(self):
        print ("creating thread {}".format (threading.currentThread().getName()))
        self.generate()
    
    def generate(self):
        cycle = 0
        while True:
            cycle=cycle+1
            with glock:
                ts1 = int(time.time_ns())
                if len (generator_queue) == 0:
                    item = self.GItem(ts1)
                    generator_queue.append(item)
                    next_item = self.GItem(ts1 + self.rate*1000000000)
                    generator_queue.append(next_item)
                else: 
                    if len (generator_queue) > 1:
                        generator_queue.pop(0)
                        next_item = self.GItem(ts1 + self.rate*1000000000)
                        generator_queue.append(next_item)
            
            
            if cycle % 2 == 0:
                frequency = HZ
            else:
                frequency = HZ * 2
          
            tone = Note(frequency).play(-1)
            time.sleep(self.beep)
            tone.stop()
            time.sleep(self.pause)
            ts2 = int(time.time_ns())
            #print (ts2-ts1)
            

class BLEProcessor(threading.Thread):

    def __init__(self, device):
        super(BLEProcessor, self).__init__(name=device)
        self.device=device

    def run(self):
        print ("# creating thread {} for {}".format (threading.currentThread().getName(), self.device))
        self.subscribe()

    def subscribe(self):
        
        connected = False
        while connected == False:
            try:
                print("connecting to LBE: ", self.device)
                p = Peripheral(self.device)
            except Exception as e:
                #print (e)
                sleep (2)
            else:
                connected = True
            
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

    class BLEItem:
        def __init__(self, ts, value, device):
            self.time = ts
            self.value = value
            self.device = device

    #Constructor (run once on startup)  
    def __init__(self, params):
        DefaultDelegate.__init__(self)
        self.device=params
        #hack to suppress duplicate notifications
        self.count = 0
      
    
    def handleNotification(self, cHandle, data):
        ts = int(time.time_ns())
        #print (str(ts) + " Notification from Device:" + self.device + ", Handle: 0x" + format(cHandle,'02X') + " Count" + str(self.count))
        if self.count == 0:
            with glock:
                if len(generator_queue) > 0:
                    gitem = generator_queue.pop(0)
                    diff = ts-gitem.ts
                    print ("difference {}, gqueue={}".format (diff/1000000, len(generator_queue)))
                    res = self.BLEItem(ts, diff, self.device)
                    results.put(res)

            self.count = self.count + 1
        else:
         if self.count > 0:
            self.count = 0


@app.before_first_request
def init():
    print ("*** in init")
    for d in sys.argv[1].split(','):
        devices.append(d.strip())

    print ("devices=", devices)

                #matcher = Matcher()
                #matcher.setDaemon(True)
                #matcher.start()
                #thread_list.append(matcher)

    generator = BitGenerator(1.5)
    generator.setDaemon(True)
    generator.start()
    thread_list.append(generator)


    for d in devices:
        thread = BLEProcessor(d)
        thread.setDaemon(True)
        thread_list.append (thread)
        thread.start()

    
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/chart-data')
    def get_responce_data():
        def generate_random_data():
            while True:
                item = results.get()
                dt = datetime.fromtimestamp(item.time // 1000000000)
                json_data = json.dumps(
                            {'time': dt.strftime('%Y-%m-%d %H:%M:%S'), 'value': item.value/1000000})
                results.task_done()
                yield f"data:{json_data}\n\n"
                time.sleep(1)

        return Response(generate_random_data(), mimetype='text/event-stream')

    @app.route('/devices')
    def list_devices():
        pass


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print ("Fatal, must pass device address:", sys.argv[0], "<device address="">")
        quit()

    #server = MyServer()

    app.run(debug=True, threaded=True, host='0.0.0.0', port=5001, use_reloader=False)

    for thread in thread_list:
        thread.join()
