
def makePack(mode, data):

    raw = bytearray()

    # Mode
    if len(mode) != 0:
        raw += b'\x01'+mode.encode('ascii')
    
    # data
    if len(data) != 0:
        raw += b'\x02'+bytes(data, 'ascii')

    # cs
    cs = 0
    raw += b'\03'
    for b in raw[1:]:
       cs += b
    cs = cs % 128
    raw += cs.to_bytes(1,'little')

    return raw

def decodePack(raw):

    chan = bytearray()
    data = bytearray()

    if len(raw) == 0:
       return chan.decode(), data.decode()

    i = 0
    cs = 0

    # Read channel
    if i <= len(raw) and raw[i] == 1:
        chan = raw[i+1:i+3]
        i += 3

        for b in chan:
            cs += b

    if i <= len(raw) and raw[i] == 2:                
        if i != 0:
            cs += 2
        i += 1

        while i <= len(raw) and raw[i] != 3:
            data += raw[i:i+1]
            i += 1

        for b in data:
            cs += b

    if i+1 <= len(raw) and raw[i] == 3:
        i += 1
        cs += 3

        cs = cs % 128
        if cs != raw[i]:
            return chan.decode(), data.decode()

    data = data.decode()
    data = data.rstrip('\r\n')

    return chan.decode(), data

def parseParamRaw(raw):
    m, ret = decodePack(raw)
    alist = ret.split('\r\n')
    for i in range(len(alist)):
        line = alist[i]
        ind = line.find('(')
        if ind != -1:
            line = line[ind+1:]
        line = line.rstrip(')')
        alist[i] = line

    return alist


# .050..
def readByMultu():
    return b'\x06\x30\x35\x30\x0D\x0A'

# .051..
def readByOne():
    return b'\x06\x30\x35\x31\x0D\x0A'

def closePacket():
    return makePack('B0', '')