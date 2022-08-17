import struct
from datetime import datetime

class TrackingMessage:
    STRUCT_FORMAT = 'Qddddddd'
    def __init__(self, client_id:int, timestamp:float, latitude:float,longitude:float, accuracy:float, speed:float,bearing:float,elapsedMs:float):
        self.client_id = client_id
        self.timestamp = timestamp
        self.latitude = latitude
        self.longitude = longitude
        self.accuracy = accuracy
        self.speed = speed
        self.bearing = bearing
        self.elapsedMs = elapsedMs

    @classmethod
    def fromTermuxLocation(cls, client_id, termux_location:dict):
        j = termux_location
        return cls(client_id, cls.getTimestampOfNow(),j['latitude'],j['longitude'],j['accuracy'],j['speed'],j['bearing'],j['elapsedMs'])

    def encode(self):
        return struct.pack(TrackingMessage.STRUCT_FORMAT,self.client_id, self.timestamp,self.latitude,self.longitude,self.accuracy,self.speed,self.bearing,self.elapsedMs)

    @classmethod
    def decode(cls, buffer:bytes):
        return cls(*struct.unpack(TrackingMessage.STRUCT_FORMAT,buffer))

    @classmethod
    def getTimestampOfNow(cls):
        return datetime.utcnow().timestamp()

    @classmethod
    def getMessageSize(cls):
        return struct.calcsize(cls.STRUCT_FORMAT)