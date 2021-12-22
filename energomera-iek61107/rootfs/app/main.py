# first written by <ivan@jad.ru> since 2021-12-20

import socket
import serial
import json
import time
import sys
import os.path
import logging
from logging.handlers import TimedRotatingFileHandler

#import paho.mqtt.client as paho_mqtt
import iek61107

logger = logging.getLogger(__name__)

def init_logger():
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(fmt="%(asctime)s %(levelname)-8s %(message)s", datefmt="%H:%M:%S")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class SDSSerial:
    def __init__(self):

        self._ser = serial.Serial()
        self._ser.port = Options["serial"]["port"]
        self._ser.baudrate = 9600
        self._ser.bytesize = serial.FIVEBITS
        self._ser.parity = serial.PARITY_EVEN
        self._ser.stopbits = serial.STOPBITS_ONE
        self._ser.timeout = 0.5

        self._ser.open()

    def close(self):
        self._soc.close()

    def send(self, a):
        self._soc.write(a)

    def sendReceive(self, req):
        self.send(req)

        data = bytearray()
        while True:
            try:
                data += self._soc.recv(8)
            except socket.error:
                break

        return data


class SDSSocket:
    def __init__(self):
        addr = Options["socket"]["address"]
        port = Options["socket"]["port"]

        self._soc = socket.socket()
        self._soc.connect((addr, port))
        self.set_timeout(0.5)

    def close(self):
        self._soc.close()

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
    logger.info("start loop ...")

    # ident
    DevIdent = conn.sendReceive(iek61107.initPacket())
    if len(DevIdent) == 0:
        DevIdent = conn.sendReceive(iek61107.initPacket())

    if len(DevIdent) == 0:
        logger.critical("Error not init")
        return

    logger.info("Init: ".DevIdent)

    # mode
    raw = conn.sendReceive(iek61107.readByOne())
    SN = iek61107.parseParamRaw(raw)
    logger.info("SN: ".SN)

def device_finish():
    logger.info("finish ...")
    conn.send( iek61107.closePacket() )

def device_loop():
    while True:
        # Read sensors
        fnc = "VOLTA()"

        raw = conn.sendReceive(iek61107.makePack('R1',fnc))
        val = iek61107.parseParamRaw(raw)
        logger.info(fnc+":", val)

        # sleep
        time.sleep(5)

def init_option(argv):

    global Options

    if len(argv) == 1:
        option_file = "./options_standalone.json"
    else:
        option_file = argv[1]

    with open(option_file) as f:
        Options = json.load(f)

    # default_file = os.path.join(os.path.dirname(os.path.abspath(argv[0])), "config.json")

    # with open(default_file) as f:
    #     config = json.load(f)
    #     logger.info("addon version {}".format(config["version"]))
    #     Options = config["options"]

    # with open(option_file) as f:
    #     Options2 = json.load(f)

    # for k, v in Options.items():
    #     if type(v) is dict and k in Options2:
    #         Options[k].update(Options2[k])
    #         for k2 in Options[k].keys():
    #             if k2 not in Options2[k].keys():
    #                 logger.warning("no configuration value for '{}:{}'! try default value ({})...".format(k, k2, Options[k][k2]))
    #     else:
    #         if k not in Options2:
    #             logger.warning("no configuration value for '{}'! try default value ({})...".format(k, Options[k]))
    #         else:
    #             Options[k] = Options2[k]

if __name__ == "__main__":
    global conn

    # configuration
    init_logger()
    init_option(sys.argv)

    if Options["serial_mode"] == "socket":
        logger.info("initialize socket...")
        conn = SDSSocket()
    else:
        logger.info("initialize serial...")
        conn = SDSSerial()

    device_init()

    try:
        device_loop()

    except:
        try:
            device_finish()
        except:
            logger.exception("finish")

        conn.close()

        logger.exception("addon finished!")