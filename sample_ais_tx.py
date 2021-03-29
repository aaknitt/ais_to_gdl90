import socket

UDP_IP = "127.0.0.1"
UDP_IP = "192.168.1.202"
UDP_PORT = 10110
#sample AIVDM NMEA messages:
#https://fossies.org/linux/gpsd/test/sample.aivdm
MESSAGE = b"!AIVDM,1,1,,A,15RTgt0PAso;90TKcjM8h6g208CQ,0*4A\r\n"
#MESSAGE = b"!AIVDM,2,1,1,A,55?MbV02;H;s<HtKR20EHE:0@T4@Dn2222222216L961O5Gf0NSQEp6ClRp8,0*1C\r\n!AIVDM,2,2,1,A,88888888880,2*25\r\n"
#MESSAGE = b"!AIVDM,2,2,1,A,88888888880,2*25"

print("UDP target IP: %s" % UDP_IP)
print("UDP target port: %s" % UDP_PORT)
print("message: %s" % MESSAGE)

sock = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP
sock.sendto(MESSAGE, (UDP_IP, UDP_PORT))