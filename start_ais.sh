#sleep 60
#cd /home/pi/rtl-ais
#screen -dmS rtl-ais-screen ./rtl_ais -n -d 2
sleep 5
cd /home/pi/gdl90
#screen -dmS ais-to-adsb-screen python3 ais_to_gdl90.py --SerialPortName /dev/dAISy  #try to start using dAISy
screen -dmS ais-to-adsb-screen python3 ais_to_gdl90.py  #try to start using dAISy
#check if dAISy startup worked
if screen -ls | grep ais >/dev/null
then
	echo "was able to start script using dAISy receiver"
else
	echo "no dAISy script found - starting aisdeco2"
	cd /home/pi/aisdeco2
	screen -dmS aisdeco2-screen ./aisdeco2 --gain 33.8 --udp 127.0.0.1:10110 --device-index 1
	sleep 5
	cd /home/pi/gdl90
	screen -dmS ais-to-adsb-screen python3 ais_to_gdl90.py
fi
