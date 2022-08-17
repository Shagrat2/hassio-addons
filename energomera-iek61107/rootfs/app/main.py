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
CONF_LOGLEVEL = 'info' # debug, info, warn
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
    },
    # {"name": "FREQU", "meas":"Hz", "dclass":"frequency", "sclass":"measurement"}, # Запрос частоты сети
    # {"name": "COS_f", "meas":"",  "dclass":"", "sclass":"measurement"}, # Коэффициенты мощности суммарный и пофазно
]

def init_option(argv):

    global Options

    if len(argv) == 1:
        option_file = "/data/options.json"
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
        logger.info(f'HTTP error occurred: {http_err}')  # Python 3.6
    except Exception as err:
        logger.info(f'Other error occurred: {err}')  # Python 3.6
    else:
        if r.status_code != 200:
            logger.info(f'Other error occurred: ' +
                        str(r.status_code)+'\r'+r.text)


def device_loop():
    while True:
        for itm in Values:
            raw = conn.sendReceive(iek61107.makePack('R1', itm["name"]+'()'))
            arr = iek61107.parseParamRaw(raw)
            for idx, val in enumerate(arr):
                key = SN+'_'+itm["name"]
                if len(arr) != 1:
                    key = key+str(idx)

                logger.info(key+":"+val+" "+itm["meas"])
                sendStates(key, val, itm)

        # sleep
        time_sleep = Options["time_sleep"]
        time.sleep(10)





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