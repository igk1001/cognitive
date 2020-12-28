import struct
import sys
import time
from bluepy.btle import UUID, Peripheral,DefaultDelegate
import threading
import queue
from time import sleep
from datetime import datetime
from utils.note import Note
from utils.analytics import get_matching_sequences
import argparse
import json
import urllib.parse
import requests
import random
import string
import pandas as pd

from flask import Flask, Response, jsonify, render_template, request

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
#results = queue.Queue()
results = []

devices = []
thread_list = []


#Admin APIs to manage a service
class Admin:
    pass

    class Device:
        def __init__(self, device, name, status):
            self.device = device
            self.name = name
            self.status = status

    class Move:
        def __init__(self, device, rate, duration):
            self.name = device.name
            self.rate = rate
            self.duration = duration


#defines desired metronome sequence
# Ex. press left hand twice, right hand once,  left hand twice, etc
#AABC
class Sequence:
    def __init__():
        self.moves = []
    
    def addMove(move):
        self.moves.append(move)



class BitGenerator(threading.Thread):
    class GItem:
        def __init__(self, ts):
            self.ts = ts

    def __init__(self, rate):
        super(BitGenerator, self).__init__(name="Generator")
        self.rate=rate
        self.beep = self.rate*0.2
        self.pause = self.rate-self.beep
        
    def init(self):
        ts1 = int(time.time_ns())
        ts2 = ts1 + self.rate*1000000000
        
        item = self.GItem(ts1)
        generator_queue.append(item)
        next_item = self.GItem(ts2)
        generator_queue.append(next_item)
       
        
    def run(self):
        print ("creating thread {}".format (threading.currentThread().getName()))
        self.generate()
    
    def generate(self):
        cycle = 0
        ts2 = 0
        while True:
            cycle=cycle+1
            with glock:
                if len (generator_queue) == 0:
                    self.init()
                else:
                    ts1 = int(time.time_ns())
                    #TODO check difference between expected (last item) and an actual during generation
                    qsize = len(generator_queue)
                    diff  = generator_queue[qsize-1].ts - ts1
                    print ("*** diff1 (ms)=", diff/1000000)
                    ts2 = ts1 + self.rate*1000000000 #TODO - logic doesnt look correct, should probably get interval from a prior beep?
        
                    item = self.GItem(ts2)
                    generator_queue.append(item)
                                
            if cycle % 2 == 0:
                frequency = HZ
            else:
                frequency = HZ
          
          #TODO -   move beeps to a different thread or a timer that executed  
            tone = Note(frequency).play(-1)
            time.sleep(self.beep)
            tone.stop()
            time.sleep(self.pause)
            ts_end = int(time.time_ns())
            diff2  = ts2 - ts_end
            print ("*** diff2 (ms)=", diff2/1000000)
deviceMap = {}

class BLEProcessor(threading.Thread):


    def __init__(self, device):
        super(BLEProcessor, self).__init__(name=device)
        self.device=device

    def run(self):
        print ("# creating thread {} for {}".format (threading.currentThread().getName(), self.device))
        self.subscribe()

    def assignDeviceName(self, device):
        index = len (deviceMap)
        name = string.ascii_uppercase [index ]
        #name = str(index+1)
        deviceMap[device] = name
        return name

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
                

        p.setDelegate( MyDelegate(self.assignDeviceName(self.device)) )

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

    

# algorithm:
# 1. generator adds timestamps to the end of the list T3 -> T2 -> T1, etc where T3>T2>T1
# 2. upon receiving a callback at a time Tcb find closest match to the generated timestamp starting from the end
# Example:
# vector = [1,2,3]
# pre-conditions: vector always has current T and next in a sequence
# input 2.7
# output 
#  2.7 - 3 = -.3
#  2.7 - 2 = 0.7
#  min (abs(-.3), abs(.7) = 0.3
#  return -.3

    def handleNotification(self, cHandle, data):
        diff = 0
        click_ts = int(time.time_ns())
        
        adjustment_ns = 0

        if self.count == 0:
            with glock:
                qsize = len(generator_queue)
                # find timestamp 
                expected1_ts = generator_queue[qsize-1].ts + adjustment_ns
                diff1 = click_ts-expected1_ts

                expected2_ts = generator_queue[qsize-2].ts + adjustment_ns
                diff2 = click_ts-expected2_ts
               

                diff = diff2 if abs (diff1) > abs (diff2) else diff1
                print ("device {}, diff1={}, diff2={}, diff {}, click={}, expected1={}, expected2={}, gqueue={}".format (self.device, round(diff1/1000000,0), round(diff2/1000000,0), round(diff/1000000,0), round(click_ts/1000000000,0), round(expected1_ts/1000000000,0), round(expected2_ts/1000000000,0), qsize))
            

            with results_lock:
                res = self.BLEItem(click_ts, diff, self.device)
                results.append(res)
        
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

    generator = BitGenerator(1.5)
    generator.setDaemon(True)
    generator.start()
    thread_list.append(generator)

    for d in devices:
        thread = BLEProcessor(d)
        thread.setDaemon(True)
        thread_list.append (thread)
        thread.start()

def createSequence():
    d1 = Device('71:35:20:99:09:EC', 'LH', '')
    d2 = Device('71:35:20:9b:bb:14', 'RH', '')
    
    seq = Sequence()
    
    seq.addMove(Move(d1, 500, 60))
    seq.addMove(Move(d1, 500, 60))
    seq.addMove(Move(d2, 500, 60))

    return seq


# Accepts pattern as a parameter. ex. http://localhost:5001/sequence?pattern=AABC  
# returns data in a following format [['AX-AX-BX-CX', 3], ['AX-BX-CX', 1], ["BX-CX", 2]]
# needs to be ordered from longest sequence to shortest
@app.route('/sequence')
def sequence():
    pattern = request.args.get('pattern')
    with results_lock:
        output = []
        items = [item.device for item in results]
        sequence = ''.join(items)
        match = get_matching_sequences(pattern,sequence)
        wordfreq = [match.count(p) for p in match]
        #print (wordfreq)
        freq_dict = dict(list(zip(match,wordfreq)))
        appender = lambda x: x + 'X'

        items = freq_dict.items()
        sorted_items = sorted(items, key=lambda x: len(x[0]), reverse=True)

        for key, value in sorted_items:
            seq=map(appender, list(key)) # hack to fix issue with single char not working
            vec = ['-'.join(seq),value]
            output.append (vec)

        #output = sorted(output, key=lambda x: x[1])
        print ('output=', json.dumps(output))
        return render_template('sequence-chart.html', data=output)
  
# returns averages per button
@app.route('/average_basic')
def average_basic():
    def generate_response():
        with results_lock:
            output = []
            devices = [item.device for item in results]
            latency = [abs(item.value/1000000) for item in results]
        
            df = pd.DataFrame({'device': devices, 'response_delay_in_ms': latency})
            print(df)
            res = df.groupby('device').agg({'device':"count", 'response_delay_in_ms':"mean"})
            print(res)
            return res.to_json()

    return Response(generate_response(), mimetype='application/json')          

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/raw-data')
def get_raw_data():
    def generate_response():
        with results_lock:
            items = [{'time': datetime.fromtimestamp(item.time // 1000000000).strftime('%Y-%m-%d %H:%M:%S'), 'value': round(item.value/1000000,0), 'device': item.device} for item in results]
            return json.dumps(items)

    return Response(generate_response(), mimetype='application/json')

@app.route('/chart-data')
def get_response_data():
    def generate_response():
        index = cursor = 0
        while True:
            with results_lock:
                length = len(results)
                for cursor in range (index, length): 
                    item = results[cursor]
                    dt = datetime.fromtimestamp(item.time // 1000000000) #ns to sec
                    json_data = json.dumps({'time': dt.strftime('%Y-%m-%d %H:%M:%S'), 'value': round(item.value/1000000,0), 'device': ord(item.device)-ord('A')}) #ns to ms
                    yield f"data:{json_data}\n\n"
                index = length
            time.sleep(0.1)

    return Response(generate_response(), mimetype='text/event-stream')

@app.route('/devices')
def list_devices():
    pass


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print ("Fatal, must pass device address:", sys.argv[0], "<device address="">")
        quit()
    
    app.static_folder = 'static'
    app.run(debug=True, threaded=True, host='0.0.0.0', port=5001, use_reloader=False)

    for thread in thread_list:
        thread.join()

