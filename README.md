# ais_to_gdl90
A small script to receive AIS data (via a UDP port from rtl-ais or via a serial port NMEA data), translate it to GDL90 data, and transmit the GDL90 data out on a UDP port.

Allows vessel locations reported via AIS to be shown as "traffic" on EFB applications such as ForeFlight, etc.  

<img src="/images/File_000.png" width="30%" height="30%">

## Setup
A source of VHF AIS data is required.  As-is, this script is set up to receive AIS data provided from an RTL SDR dongle by [rtl-ais](https://github.com/dgiardini/rtl-ais) via a UDP port or from NMEA serial data from a receiver such as the [dAISy HAT](https://shop.wegmatt.com/products/daisy-hat-ais-receiver?variant=7103554977828).

rtl-ais and this script can be installed on a Stratux or a standalone Raspberry Pi used only for VHF AIS reception.  If installed on a Stratux, an additional SDR dongle used to receive the VHF AIS data is required.  If installed on another Pi, that second Pi should be connected to the Stratux WiFi network.  

## Dependencies
To install rtl-ais, follow the instructions at:
https://github.com/dgiardini/rtl-ais

AIS sentence decoding in Python:
https://github.com/M0r13n/pyais

install pip3 (not installed by default on a Stratux):
```
sudo apt-get install python3-pip
```
install pyais:
```
pip3 install pyais
```
PySerial is needed to get AIS data from a serial port source such as a dAISy receiver (instead of rtl-ais)
```
pip3 install pyserial
```
A partial fork of the [gdl90](https://github.com/etdey/gdl90) library is used to encode the gdl90 data.  This partial fork is included in this repository, so installing it separately is not required.  Modifications were made to adapt it for compatibility with Python 3 since the pyais library requires Python 3.  
## Running
Once installed, rtl-ais can be run as follows (example: use rtl-sdr device index 2, receive AIS traffic, send UDP NMEA sentences to 127.0.0.1 port 10110 and log the sentences to console):
```
./rtl_ais -n -d 2  
```
Once rtl-ais is running, this script can be run with:
```
python3 ais_to_gdl90.py
```
Or to run using a serial port AIS receiver (instead of rtl-ais):
``` 
python3 ais_to_gdl90.py --SerialPortName /dev/ttyUSB0 --SerialPortBaud 38400
```
## Persistant device names when using multiple USB serial devices
On a Stratux it's common to have multiple devices that act as USB serial ports (GPS and UAT receivers, for example).  When adding an AIS receiver (such as a dAISy), the /dev/ttyUSBx or /dev/ttyACMx names that the OS gives to each device may vary on startup.  The best way to address this is to create udev rules that create a persistant symlink name for your AIS receiver.  The process is explained well [here](http://hintshop.ludvig.co.nz/show/persistent-names-usb-serial-devices/).

As an example, the udev rule that I created for my dAISy reciever (this line is placed in the file /etc/udev/rules.d/99-usb-serial.rules) looks like this:
```
SUBSYSTEM=="tty", ATTRS{idVendor}=="16d0", ATTRS{idProduct}=="0b03", SYMLINK+="dAISy"
```
My startup script (that I start automatically on boot via a crontab entry) then looks like this:
```
cd /home/pi/gdl90
screen -dmS ais-to-adsb-screen python3 ais_to_gdl90.py --SerialPortName /dev/dAISy
```
Note that in this example I'm use the 'screen' utility to allow me to easily connect and monitor the script via SSH, but that's not required.  

## Limitations
* The GDL90 data format only allocates 8 ASCII characters for the "callsign" field so vessel names received via AIS will be truncated to 8 characters when sent via GDL90
* AIS data does not included altitude.  GDL90 data is currently populated with an altitude of 0 ft MSL.  
* While AIS position reports are sent every 2 to 10 seconds while underway, static reports that contain the vessel name are only sent every 6 minutes.  If a position report is received before a static report is received, the first 8 characters of the MMSI are used to populate the GDL90 "callsign" field.  Once the vessel name has been recieved via a static report, the "callsign" field will change to the first 8 characters of the vessel name. MMSI to vessel name mapping is stored in a JSON file for later use after restarts.  
