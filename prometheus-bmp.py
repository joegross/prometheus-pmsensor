#!/usr/bin/env python3

import argparse
import logging
import time

from BMP280 import BMP280
from prometheus_client import Gauge, start_http_server

logger = logging.getLogger(__name__)

LISTEN_PORT = 8003
LOOP_SLEEP_TIME = 5


class sensor_server(object):
    def __init__(self, listen_port, sleep=LOOP_SLEEP_TIME):
        self.sleep = sleep
        self.sensor = BMP280.BMP280()
        start_http_server(listen_port)
        self.bmp_pressure = Gauge(
            'bmp_pressure', 'Pressure in Pa')
        self.bmp_altitude = Gauge(
            'bmp_altitude', 'Altitude in M')
        self.bmp_temperature = Gauge(
            'bmp_temperature', 'Temperature in C')

    def post_data(self, pressure, altitude, temperature):
        logging.info("BMP: pressure: %s altitude: %s temperature: %s",
                     pressure, altitude, temperature)
        self.bmp_pressure.set(pressure)
        self.bmp_altitude.set(altitude)
        self.bmp_temperature.set(temperature)

    def serve_forever(self):
        while True:
            try:
                pressure = self.sensor.read_pressure()
                altitude = self.sensor.read_altitude()
                temperature = self.sensor.read_temperature()
            except Exception as e:
                logging.warning(e)
            if pressure:
                self.post_data(pressure, altitude, temperature)
            logging.debug("sleeping %s...", self.sleep)
            time.sleep(self.sleep)


def init_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format='%(asctime)s %(name)-18s %(levelname)-8s %(message)s'
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-p', '--listen_port',
                        default=LISTEN_PORT, help='listen port')
    args = parser.parse_args()
    if args.verbose:
        init_logging(logging.DEBUG)
    else:
        init_logging(logging.INFO)
    sensor_server(args.listen_port).serve_forever()
