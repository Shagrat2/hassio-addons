# first written by <ivan@jad.ru> since 2021-12-20

import socket
import serial
import paho.mqtt.client as paho_mqtt
import logging
from logging.handlers import TimedRotatingFileHandler

logger = logging.getLogger(__name__)

def init_logger():
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(fmt="%(asctime)s %(levelname)-8s %(message)s", datefmt="%H:%M:%S")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def init_logger_file():
    if Options["log"]["to_file"]:
        filename = Options["log"]["filename"]
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        formatter = logging.Formatter(fmt="%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        handler = TimedRotatingFileHandler(os.path.abspath(Options["log"]["filename"]), when="midnight", backupCount=7)
        handler.setFormatter(formatter)
        handler.suffix = '%Y%m%d'
        logger.addHandler(handler)

if __name__ == "__main__":
    global conn

    # configuration 로드 및 로거 설정
    init_logger()
    init_option(sys.argv)
    init_logger_file()

    init_virtual_device()

    if Options["serial_mode"] == "socket":
        logger.info("initialize socket...")
        conn = SDSSocket()
    else:
        logger.info("initialize serial...")
        conn = SDSSerial()

    dump_loop()

    start_mqtt_loop()

    try:
        # 무한 루프
        serial_loop()
    except:
        logger.exception("addon finished!")