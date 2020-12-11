from bluepy import btle
import sys
import binascii
import struct
import time

# 1. Device 71:35:20:99:09:EC TECELKS
# 2. Device FF:FF:D0:00:EF:18 TECELKS
 
print ("Connecting...")
dev = btle.Peripheral("FF:FF:D0:00:EF:18")
#dev = btle.Peripheral("71:35:20:99:09:EC")

 
print ("Services...")
for svc in dev.services:
	print (str(svc))
	for ch in svc.getCharacteristics():
		print (ch.propertiesToString(), ch.uuid)
		#if ch.uuid == "00002a4d-0000-1000-8000-00805f9b34fb":
		#if ch.uuid == "00002a4b-0000-1000-8000-00805f9b34fb":	
		if ch.uuid == "00002a4a-0000-1000-8000-00805f9b34fb":
			if (ch.supportsRead()):
				while 1:            				
					val = ch.read()
					s =  str(binascii.b2a_hex(val))
					if s != "b'0000'":
						print (int(time.time() * 1000), ", pressed", s)
					time.sleep(0.020)
