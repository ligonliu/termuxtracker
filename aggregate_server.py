#!/usr/bin/env python3

from TrackingMessage import TrackingMessage

if __name__ == '__main__':
    import socket

    UDP_IP = "192.168.230.27"
    UDP_PORT = 5200

    sock = socket.socket(socket.AF_INET, # Internet
                         socket.SOCK_DGRAM) # UDP
    sock.bind((UDP_IP, UDP_PORT))

    while True:
        data, addr = sock.recvfrom(2048) # buffer size is 2048 bytes
        if len(data)==TrackingMessage.getMessageSize():
            msg = TrackingMessage.decode(data)
            print(msg.__dict__)
        else:
            print("ERR: Message length {0}, expected {1}".format(len(data), TrackingMessage.getMessageSize()))

    