#!/usr/bin/env python

import socket
import sys

import iek61107

Host = '10.9.2.2'
Port = 3001

def sendReceive(req):

    s.send(req)

    data = bytearray()
    while True:
        try:
            data += s.recv(8)
        except socket.error:
            break

    return data

# Connect
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(4)
s.connect((Host, Port))

# Settings
s.settimeout(1)

# Init /?!.. -> b'/EKT5CE102Mv01\r\n'
DevIdent = sendReceive(b'\x2F\x3F\x21\x0D\x0A')
if len(DevIdent) == 0: 
    DevIdent = sendReceive(b'\x2F\x3F\x21\x0D\x0A')

if len(DevIdent) == 0: 
    print("Error not init")
    s.close()
    sys.exit(1)

print("Init:", DevIdent)

# # Read all .050..
# raw = sendReceive(iek61107.readByMultu())
# m, INFO = iek61107.decodePack(raw)
# print(INFO)

# Read Serrial .051..
raw = sendReceive(iek61107.readByOne())
SN = iek61107.parseParamRaw(raw)
print("SN:", SN)

#===== params ====

#params = ["ET0PE()", "MODEL()", "SNUMB()", "VOLTA()", "CURRE()", "POWEP()", "FREQU()", "COS_f()"]
params = ["ET0PE()", "VOLTA()", "CURRE()", "POWEP()"]

for fnc in params:
    raw = sendReceive(iek61107.makePack('R1',fnc))
    val = iek61107.parseParamRaw(raw)
    print(fnc+":", val)
    
# close
s.send( iek61107.closePacket() )
s.close()
