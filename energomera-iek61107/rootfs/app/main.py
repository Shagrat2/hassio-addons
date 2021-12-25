# first written by <ivan@jad.ru> since 2021-12-20

import socket
import serial
import json
import time
import sys
import os.path
import logging
import requests
from requests.exceptions import HTTPError
from logging.handlers import TimedRotatingFileHandler

import iek61107

logger = logging.getLogger(__name__)


def init_logger():
    logger.setLevel(logging.INFO)

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

        self._ser.open()

    def close(self):
        self._ser.close()

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

    global DevIdent
    global SN

    # close
    conn.send(iek61107.closePacket())

    # ident
    DevIdent = conn.sendReceive(iek61107.initPacket())
    if len(DevIdent) == 0:
        DevIdent = conn.sendReceive(iek61107.initPacket())

    if len(DevIdent) == 0:
        logger.critical("Error not init")
        return

    DevIdent = DevIdent.decode('UTF-8').rstrip('\r\n')
    if DevIdent == "ERR11":
        logger.critical("Error 11")
        return

    logger.info("Init: "+DevIdent)

    # mode
    raw = conn.sendReceive(iek61107.readByOne())
    aSN = iek61107.parseParamRaw(raw)
    SN = aSN[0]
    logger.info("SN: "+SN)

    return SN


def device_finish():
    conn.send(iek61107.closePacket())
    logger.info("finish ...")


def sendStates(eid, val, meas):
    host = "172.30.32.1"
    access_token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiI1NjY5YThlOTQxM2M0M2VkOTg0OGVhYTViMDc0MmM3OCIsImlhdCI6MTY0MDQyMzAyMSwiZXhwIjoxOTU1NzgzMDIxfQ.dN3DEBWmKPiJx_Of5JtF0Rs5MzqoqlK_ggczCKJRqQ8'

    json_headers = {
        "Content-type": "application/json",
        "Authorization": "Bearer %s" % access_token
    }
    payload = {
        "state": val,
        "attributes": {
            "unit_of_measurement": meas
        }
    }

    try:
        r = requests.post('http://'+host+':8123/api/states/sensor.' +
                          eid, headers=json_headers, json=payload, verify=False)

    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')  # Python 3.6
    except Exception as err:
        print(f'Other error occurred: {err}')  # Python 3.6
    else:
        if r.status_code != 200:
            print(f'Other error occurred: '+r.status_code+'\r'+r.text)


def device_loop():
    while True:
        # Read sensors
        params = [
            {"name": "ET0PE", "meas": "kw/h"},
            {"name": "VOLTA", "meas": "V"},
            {"name": "CURRE", "meas": "A"},
            {"name": "POWEP", "meas": "kw"}
        ]

        for itm in params:
            raw = conn.sendReceive(iek61107.makePack('R1', itm["name"]+'()'))
            arr = iek61107.parseParamRaw(raw)
            for idx, val in enumerate(arr):
                key = SN+'_'+itm["name"]
                if len(arr) != 1:
                    key = key+str(idx)

                logger.info(key+":"+val+" "+itm["meas"])
                sendStates(key, val, itm["meas"])

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

    if device_init() == "":
        conn.close()
        sys.exit(1)

    try:
        device_loop()

    except:
        try:
            device_finish()
        except:
            logger.exception("finish")

        conn.close()

        logger.exception("addon finished!")
