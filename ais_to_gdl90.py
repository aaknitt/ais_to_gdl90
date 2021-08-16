#!/usr/bin/env python
from pyais.stream import UDPStream
from pyais.messages import NMEAMessage
from pyais.decode import decode
import time
import os
import socket
import gdl90.encoder
import random
import json
import _thread
import serial
import serial.tools.list_ports
import argparse

# Default values for options
#DEF_TX_ADDR="192.168.10.255"
DEF_TX_PORT=4000
DEF_RX_ADDR = "127.0.0.1"
DEF_RX_PORT = 10110

parser = argparse.ArgumentParser(description='Convert AIS data to ADS-B data for displaying vessel location in ForeFlight and other EFBs')
parser.add_argument('--SerialPortName',dest='SerialPortName', help='Name of Serial Port to recieve AIS data in NMEA format')
parser.set_defaults(SerialPortName='')
parser.add_argument('--SerialPortBaud',dest='SerialPortBaud', help='Baud rate of serial port to receive AIS data in NMEA format')
parser.set_defaults(SerialPortBaud=38400)
parser.add_argument('--Broadcast',dest='BROADCAST', help='Set to 1 to send ADS-B data via UDP broadcast in addition to unicast to detected ForeFlight instances')
parser.set_defaults(BROADCAST=0)

args = parser.parse_args()
BROADCAST = int(args.BROADCAST)

SerialPortName = str(args.SerialPortName)
SerialPortBaud = int(args.SerialPortBaud)

if SerialPortName == '':
	#No serial port specified, search for dAISy
	serialPorts = serial.tools.list_ports.comports()
	for serialPort in serialPorts:
		if 'dAISy' in serialPort.description:
			print("found dAISY on port " + serialPort.device)
			SerialPortName = serialPort.device
			SerialPortBaud = 38400
else:
	print("using serial port specified by argument " + SerialPortName)

encoder = gdl90.encoder.Encoder()

if os.name != "nt":
	import fcntl
	import struct
	def get_interface_ip(ifname):
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		return socket.inet_ntoa(fcntl.ioctl(
				s.fileno(),
				0x8915,  # SIOCGIFADDR
				struct.pack('256s', bytes(ifname[:15], 'utf-8'))
				# Python 2.7: remove the second argument for the bytes call
			)[20:24])

def get_ips():
	ips = []
	ip = socket.gethostbyname(socket.gethostname())
	ips.append(ip)
	if ip.startswith("127.") and os.name != "nt":
		interfaces = ["eth0","eth1","eth2","wlan0","wlan1","wifi0","ath0","ath1","ppp0"]
		ips = []
		for ifname in interfaces:
			try:
				ip = get_interface_ip(ifname)
				ips.append(ip)
			except IOError:
				pass
	return ips


ips = get_ips()

broadcast_ips = []
for ip in ips:
	split = ip.split('.')
	split[-1] = '255'
	broadcast_ip = ".".join(split)
	broadcast_ips.append([broadcast_ip, DEF_TX_PORT])
	
print(broadcast_ips)

foreflight_ips = []

try:
	with open('mmsi.json') as f:
		mmsidict = json.load(f)
except:
	mmsidict = {}

positions = {}


print("Simulating Stratux unit.")

for ip, port in broadcast_ips:
	if BROADCAST == 1:
		print(("Broadcasting GLD90 data to %s:%s" % (ip, port)))

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

def sendtolist(buf,broadcast_ips,foreflight_ips,send_broadcast=1):
	if send_broadcast == 1:
		address_list = broadcast_ips + foreflight_ips
	else:
		address_list = foreflight_ips
	for ip ,port in address_list:
		s.sendto(buf, (ip, port))

def send_gdl90():
	#send GDL90 data once per second
	#ADSB messages are sent much more frequently than AIS.  We need to repeat AIS messages so that the GDL90 receiver
	#(ForeFlight, etc.) keeps the AIS targets active on the display without it timing out.
	while True:
		# Heartbeat Messages
		buf = encoder.msgHeartbeat()
		sendtolist(buf,broadcast_ips,foreflight_ips,BROADCAST)		# Stratux Heartbeat Message
		buf = encoder.msgStratuxHeartbeat()
		sendtolist(buf,broadcast_ips,foreflight_ips,BROADCAST)		# Hiltonsoftware SX Heartbeat Message
		buf = encoder.msgSXHeartbeat(towers=[])
		sendtolist(buf,broadcast_ips,foreflight_ips,BROADCAST)		#Send AIS position reports
		#print(time.time())
		for mmsi in positions:
			print(mmsi)
			data = positions[mmsi][0]
			callsign = positions[mmsi][2]
			timestamp = positions[mmsi][1]
			if time.time()-timestamp < 180:
				#address = random.randrange(0,2**24)
				address=int(mmsi[-6:])
				#address = 7760443  #VALID
				# not valid:  5750039  
				#print(address)
				#only send AIS data if it's been received within that last three minutes
				#send a GDL90 message out via UDP message - AIS data gets loaded into GDL90 message
				'''
				#This section is for testing when onboard the ferries - ForeFlight won't show traffic if it's in the exact same location
				#as I am, so add in an artificial offset during testing
				if callsign == "BADGER" or callsign =="LAKE EXP":
					sendlat = data['lat'] + .02
				else:
					sendlat = data['lat']
				'''
				buf = encoder.msgTrafficReport(latitude=sendlat, longitude=data['lon'],altitude=0, hVelocity=data['speed'], vVelocity=0, trackHeading=data['course'], callSign=callsign, address=address,emitterCat=18)
				#print(int(mmsi[-6:]))
				#buf = encoder.msgTrafficReport(latitude=data['lat'], longitude=data['lon'],altitude=0, hVelocity=data['speed'], vVelocity=0, trackHeading=data['course'], callSign=callsign, address=int(mmsi[-6:]),emitterCat=18)
				sendtolist(buf,broadcast_ips,foreflight_ips,BROADCAST)				#print(buf)
		time.sleep(1)
	
def rx_foreflight(ip):
	global foreflight_ips
	UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
	UDPServerSocket.bind((ip,63093))
	print("listening for ForeFlight heartbeats on " + ip + " port 63093")
	while(True):
		bytesAddressPair = UDPServerSocket.recvfrom(1024)
		message = bytesAddressPair[0]
		address = bytesAddressPair[1]
		clientMsg = "Message from Client:{}".format(message)
		clientIP = "Client IP Address:{}".format(address)
		json_msg = json.loads(message)
		if json_msg['App'] == 'ForeFlight':
			if [address[0],json_msg['GDL90']['port']] not in foreflight_ips:
				foreflight_ips.append([address[0],json_msg['GDL90']['port']])
				print("Adding ForeFlight client at " + address[0] + " port " + str(json_msg['GDL90']['port']))
				print(foreflight_ips)

_thread.start_new_thread(send_gdl90,())
for ip, port in broadcast_ips:
	_thread.start_new_thread(rx_foreflight,(ip,))

def handle_ais_data(data):
	global positions, mmsidict
	if data['type'] in [1,2,3]:
		#it's a position report
		if data['mmsi'] in mmsidict:
			callsign = mmsidict[data['mmsi']][0:8]
		else:
			callsign = str(data['mmsi'])[0:8]
		positions[data['mmsi']] = [data,time.time(),callsign]
		print(positions[data['mmsi']])
		
	elif data['type'] == 5:
		#it's a ship static report - this is where we get vessel name and link it to the MMSI
		mmsidict[data['mmsi']] = data['shipname']
		with open('mmsi.json', 'w') as json_file:
			json.dump(mmsidict, json_file)  #store vessel names for later use since they only get transmitted every 6 minutes
			
if SerialPortName != '':
	try:
		serial = serial.Serial( SerialPortName, SerialPortBaud, timeout=1 )
		print("Opened the serial port - waiting for NMEA AIS data")
	except:
		#kill the program - couldn't open the serial port
		print("Unable to open the serial port " + SerialPortName + " - unable to proceed - exiting")
		os._exit(1)
	while True:
		line = serial.readline()
		if line != b'':
			print(line)
			message = NMEAMessage(line)
			try:
				data = decode(message)
				handle_ais_data(data)
			except:
				pass  #prevent crashing when an unsupported AIS message is received

	
	
else:
	print("listening for AIS data on " + DEF_RX_ADDR + " port " + str(DEF_RX_PORT))
	for msg in UDPStream(DEF_RX_ADDR, DEF_RX_PORT):
		#AIS data comes in from rtl-ais via UDP port
		print(msg)
		data = msg.decode()
		#print(data)
		handle_ais_data(data)
			

