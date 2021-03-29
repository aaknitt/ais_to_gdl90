#!/usr/bin/env python
from pyais.stream import UDPStream
import time
import socket
import gdl90.encoder
import random
import json
import _thread

# Default values for options
DEF_TX_ADDR="192.168.10.255"
DEF_TX_PORT=4000
DEF_RX_ADDR = "127.0.0.1"
DEF_RX_PORT = 10110
encoder = gdl90.encoder.Encoder()

try:
	with open('mmsi.json') as f:
		mmsidict = json.load(f)
except:
	mmsidict = {}

positions = {}

print("listening for AIS data on " + DEF_RX_ADDR + " port " + str(DEF_RX_PORT))
print("Simulating Stratux unit.")
print(("Transmitting GLD90 data to %s:%s" % (DEF_TX_ADDR, DEF_TX_PORT)))

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

def send_gdl90():
	#send GDL90 data once per second
	#ADSB messages are sent much more frequently than AIS.  We need to repeat AIS messages so that the GDL90 receiver
	#(ForeFlight, etc.) keeps the AIS targets active on the display without it timing out.
	while True:
		# Heartbeat Messages
		buf = encoder.msgHeartbeat()
		s.sendto(buf, (DEF_TX_ADDR, DEF_TX_PORT))
		# Stratux Heartbeat Message
		buf = encoder.msgStratuxHeartbeat()
		s.sendto(buf, (DEF_TX_ADDR, DEF_TX_PORT))
		# Hiltonsoftware SX Heartbeat Message
		buf = encoder.msgSXHeartbeat(towers=[])
		s.sendto(buf, (DEF_TX_ADDR, DEF_TX_PORT))
		#Send AIS position reports
		for mmsi in positions:
			data = positions[mmsi][0]
			timestamp = positions[mmsi][1]
			if time.time()-timestamp < 180:
				#only send AIS data if it's been received within that last three minutes
				#send a GDL90 message out via UDP message - AIS data gets loaded into GDL90 message
				buf = encoder.msgTrafficReport(latitude=data['lat'], longitude=data['lon'],altitude=0, hVelocity=data['speed'], vVelocity=0, trackHeading=data['course'], callSign=callsign, address=random.randrange(0,2**24),emitterCat=18)
				s.sendto(buf, (DEF_TX_ADDR, DEF_TX_PORT))
		time.sleep(1)
	
_thread.start_new_thread(send_gdl90,())

for msg in UDPStream(DEF_RX_ADDR, DEF_RX_PORT):
	#AIS data comes in from rtl-ais via UDP port
	print(msg)
	data = msg.decode()
	print(data)
	if data['type'] in [1,2,3]:
		#it's a position report
		if data['mmsi'] in mmsidict:
			callsign = mmsidict[data['mmsi']][0:8]
		else:
			callsign = str(data['mmsi'])[0:8]
		positions[data['mmsi']] = [data,time.time()]
		
	elif data['type'] == 5:
		#it's a ship static report - this is where we get vessel name and link it to the MMSI
		mmsidict[data['mmsi']] = data['shipname']
		with open('mmsi.json', 'w') as json_file:
			json.dump(mmsidict, json_file)  #store vessel names for later use since they only get transmitted every 6 minutes
			

