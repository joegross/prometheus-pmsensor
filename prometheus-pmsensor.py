#!/usr/bin/env python3

import argparse
import logging
import termios
import time
import serial
from pmsensor import co2sensor
from prometheus_client import start_http_server, Gauge

logger = logging.getLogger(__name__)

LISTEN_PORT = 8001
CO2_SERIAL = '/dev/tty.usbserial'
CO2_PREHEAT_TIME = 300 # seconds
CO2_PREHAT_VALUES = [400, 410, 1215]
CO2_MAX_PPM = 5000 # anything higher is absurd
LOOP_SLEEP_TIME = 5

class sensor_server(object):
    def __init__(self, listen_port, serial_port, sleep=LOOP_SLEEP_TIME):
        self.sleep = sleep
        self.serial_port = serial_port
        start_http_server(listen_port)
        self.co2_ppm = Gauge('co2_ppm', 'CO2 concentration in PPM', ['serial_port'])
        self.co2_temp = Gauge('co2_temp', 'CO2 sensor temp in C', ['serial_port'])

    def post_data(self, res):
        ppm, temp = res
        logging.info("CO2: %s ppm, temp: %s C", ppm, temp)
        # do not post preheat values
        if ppm in CO2_PREHAT_VALUES:
            logging.warning("CO2 preheating: Not posting.")
            return
        # pmsensor does not checksum
        if ppm > CO2_MAX_PPM:
            logging.warning("CO2 over max: Not posting.")
            return
        self.co2_ppm.labels(serial_port=self.serial_port).set(ppm)
        self.co2_temp.labels(serial_port=self.serial_port).set(temp)

    def serve_forever(self):
        while True:
            res = None
            try:
                res = co2sensor.read_mh_z19_with_temperature(self.serial_port)
            except (serial.serialutil.SerialException, termios.error) as e:
                logging.warning(e)
            if res:
                self.post_data(res)
            logging.debug("sleeping %s...", self.sleep)
            time.sleep(self.sleep)

def init_logging(level=logging.INFO):
    logging.basicConfig(level=level, format='%(asctime)s %(name)-18s %(levelname)-8s %(message)s')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-s', '--serial_port', default=CO2_SERIAL, help='serial port path')
    parser.add_argument('-p', '--listen_port', default=LISTEN_PORT, help='listen port')
    args = parser.parse_args()
    if args.verbose:
        init_logging(logging.DEBUG)
    else:
        init_logging(logging.INFO)
    sensor_server(args.listen_port, args.serial_port).serve_forever()
