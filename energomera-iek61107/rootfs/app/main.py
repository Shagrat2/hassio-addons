# first written by <ivan@jad.ru> since 2021-12-20
# Protocol https://shop.energomera.kharkov.ua/DOC/CE303U/data_transf_descr_GOST-IES-61107-2011.pdf

import socket
import serial
import json
import time
import sys
import os.path
import logging
import requests
import logging.config
import logging.handlers
import configparser
from requests.exceptions import HTTPError
from logging.handlers import TimedRotatingFileHandler

# Log Level
#CONF_LOGLEVEL = 'info' # debug, info, warn
RECONNECT_TIME = 10 # 10 sec - before reconnect

import iek61107

logger = logging.getLogger(__name__)

# Read sensors
Values = [
    {   # Сумма
        "name": "ET0PE",
        "meas": "kWh",
        "dclass": "energy",
        "sclass": "total",
        "last_reset": None,
    },
    {   # Действующее значение напряжения
        "name": "VOLTA",
        "meas": "V",
        "dclass": "voltage",
        "sclass": "measurement",
    },
    {   # Действующее значение тока
        "name": "CURRE",
        "meas": "A",
        "dclass": "current",
        "sclass": "measurement",
    },
    {   # Действующее значение потребления
        "name": "POWEP",
        "meas": "kW",
        "dclass": "power",
        "sclass": "measurement",
    },
    {   # Действующее значение потребления пофазно
        "name": "POWPP",
        "meas": "kW",
        "dclass": "power",
        "sclass": "measurement",
    },  # Запрос частоты сети
    {   "name": "FREQU", 
        "meas":"Hz", 
        "dclass":"frequency", 
        "sclass":"measurement",
    },  # Коэффициенты мощности суммарный и пофазно
    {   "name": "COS_f", 
        "meas":"",  
        "dclass":"", 
        "sclass":"measurement",
    }, 
]

IgnoreList = []

def init_option(argv):

    global Options

    if len(argv) == 1:
        option_file = "/data/options.json"
    else:
        option_file = argv[1]

    with open(option_file) as f:
        Options = json.load(f)

def init_logger(logLevel):
    logger.setLevel(logLevel)

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)-8s %(message)s", datefmt="%H:%M:%S")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class SDSSerial:
    def __init__(self):

        self._ser = serial.Serial()
        self._ser.port = Options["serial"]["port"]
        self._ser.baudrate = 9600
        self._ser.bytesize = serial.SEVENBITS
        self._ser.parity = serial.PARITY_EVEN
        self._ser.stopbits = serial.STOPBITS_ONE
        self._ser.timeout = 0.5
        
    def open(self):
        try:
            self._ser.open()
            return True
        except Exception as err:
            logger.error("Error open socket: "+err)
            return False

    def close(self):
        try:
            self._ser.close()
            return True
        except:
            return False

    def send(self, a):
        self._ser.write(a)

    def sendReceive(self, req):
        self.send(req)

        data = bytearray()
        while True:
            ch = self._ser.read()
            if len(ch) == 0:
                break
            data += ch
        return data


class SDSSocket:
    def __init__(self):
        self._soc = socket.socket()
        self.set_timeout(0.5)        

    def open(self):
        addr = Options["socket"]["address"]
        port = Options["socket"]["port"]
        try:
            self._soc.connect((addr, port))
            return True
        except Exception as err:
            logger.error("Error open socket: "+err)
            return False

    def close(self):
        try:
            self._soc.close()
            return True
        except:
            return False

    def send(self, a):
        self._soc.sendall(a)

    def sendReceive(self, req):
        self.send(req)

        data = bytearray()
        while True:
            try:
                data += self._soc.recv(8)
            except socket.error:
                break

        return data


def device_init():
    global DevIdent
    global SN

    try:
        # close
        conn.send(iek61107.closePacket())

        # ident
        DevIdent = conn.sendReceive(iek61107.initPacket())
        if len(DevIdent) == 0:
            DevIdent = conn.sendReceive(iek61107.initPacket())

        if len(DevIdent) == 0:
            logger.critical("Error not init")
            return ""

        DevIdent = DevIdent.decode('UTF-8').rstrip('\r\n')
        if DevIdent == "ERR11":
            logger.critical("Error 11")
            return ""

        logger.info("Init: "+DevIdent)

        # mode
        raw = conn.sendReceive(iek61107.readByOne())
        aSN = iek61107.parseParamRaw(raw)
        SN = aSN[0]
        logger.info("SN: "+SN)

        return SN

    except Exception as err:
        logger.error("Error init: "+err)
        return ""
       

def device_finish():
    logger.debug("finish ...")
    try:
        conn.send(iek61107.closePacket())
        return True

    except serial.serialutil.PortNotOpenError as err:        
        return False

    except:
        logger.error("Error send device finish: ", err)
        return False


def sendStates(eid, val, valClass):
    host = Options["host_ip"]
    access_token = Options["auth_key"]

    json_headers = {
        "Content-type": "application/json",
        "Authorization": "Bearer %s" % access_token
    }
    payload = {
        "state": val,
        "unique_id": 'sensor.' + eid,
        "entity_id": 'sensor.' + eid,
        "attributes": {
            "device_class": valClass["dclass"],
            "state_class": valClass["sclass"],
            "unit_of_measurement": valClass["meas"],
        },
    }
    if "last_reset" in valClass:
        payload["last_reset"] = valClass["last_reset"]

    try:
        r = requests.post('http://'+host+':8123/api/states/sensor.' +
                          eid, headers=json_headers, json=payload, verify=False)

    except HTTPError as http_err:
        logger.error(f'HTTP error occurred: {http_err}')  # Python 3.6
    except Exception as err:
        logger.error(f'Other error occurred: {err}')  # Python 3.6
    else:
        if not (r.status_code == 200 or r.status_code == 201):
            logger.error(f'Other error occurred: ' +
                        str(r.status_code)+'\r'+r.text)


def device_loop():
    while True:

        logger.debug("=== Read data")

        for itm in Values:
            # Skip not suported
            if itm["name"] in IgnoreList:
                continue

            # Read fron device
            raw = conn.sendReceive(iek61107.makePack('R1', itm["name"]+'()'))
            if not raw:
                return False

            arr = iek61107.parseParamRaw(raw)
            for idx, val in enumerate(arr):

                if val == "ERR12":

                    logger.info("Parameter not supported: "+itm["name"])

                    IgnoreList.append(itm["name"])
                    continue

                key = SN+'_'+itm["name"]
                if len(arr) != 1:
                    key = key+str(idx)

                logger.debug(key+":"+val+" "+itm["meas"])
                sendStates(key, val, itm)

        # sleep
        time_sleep = Options["time_sleep"]
        time.sleep(time_sleep)

    return True


if __name__ == "__main__":
    global conn

    # configuration
    init_option(sys.argv)

    # log
    logLevel = logging.INFO
    if Options["debug"]:
        logLevel = logging.DEBUG
    init_logger(logLevel)

    #  mode
    if Options["serial_mode"] == "socket":
        logger.info("initialize socket...")
        conn = SDSSocket()
    else:
        logger.info("initialize serial...")
        conn = SDSSerial()

    while True:

        # Close last        
        device_finish()
        conn.close()

        # Open connection
        logger.debug("Open connection ...")
        if not conn.open():
            time.sleep(RECONNECT_TIME)
            continue

        # Init
        logger.debug("Init ...")
        if device_init() == "":
            time.sleep(RECONNECT_TIME)
            continue

        # Loop info
        logger.debug("Read data ...")
        if device_loop():
            break # Nornal exit

        # Reconnect
        time.sleep(RECONNECT_TIME)
        
    # End session    
    device_finish()

    # Close device
    conn.close()

    logger.info("Programm STOP")