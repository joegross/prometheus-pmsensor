#!/usr/bin/env python3

import argparse
import copy
import logging
import time

from prometheus_client import Gauge, start_http_server

import bme680

logger = logging.getLogger(__name__)

LISTEN_PORT = 8003
LOOP_SLEEP_TIME = 5


class sensor_server(object):
    def __init__(self, listen_port, sleep=LOOP_SLEEP_TIME):
        self.sleep = sleep
        self.sensor = bme680.BME680(i2c_addr=0x77)
        self.set_sensor_oversamping()
        self.set_sensor_heater_profile()
        while not self.sensor.get_sensor_data() and not self.sensor.data.heat_stable:
            logging.info("sensor not ready, sleeping 1...")
            time.sleep(1)
        start_http_server(listen_port)
        self.bme_temperature = Gauge(
            'bme_temperature', 'bme_temperature in DegC').set_function(lambda: self.sensor.data.temperature)
        self.bme_pressure = Gauge(
            'bme_pressure', 'bme_pressure in hPa').set_function(lambda: self.sensor.data.pressure)
        self.bme_humidity = Gauge(
            'bme_humidity', 'bme_humidity in %RH').set_function(lambda: self.sensor.data.humidity)
        self.bme_gas_resistance = Gauge(
            'bme_gas_resistance', 'bme_gas_resistance in Ohm').set_function(lambda: self.sensor.data.gas_resistance)

    def set_sensor_oversamping(self):
        self.sensor.set_humidity_oversample(bme680.OS_2X)
        self.sensor.set_pressure_oversample(bme680.OS_4X)
        self.sensor.set_temperature_oversample(bme680.OS_8X)
        self.sensor.set_filter(bme680.FILTER_SIZE_3)
        self.sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)

    def set_sensor_heater_profile(self):
        self.sensor.set_gas_heater_temperature(320)
        self.sensor.set_gas_heater_duration(150)
        self.sensor.select_gas_heater_profile(0)

    def serve_forever(self):
        while True:
            self.sensor.get_sensor_data()
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
    parser.add_argument('-p', '--listen_port', type=int,
                        default=LISTEN_PORT, help='listen port')
    args = parser.parse_args()
    if args.verbose:
        init_logging(logging.DEBUG)
    else:
        init_logging(logging.INFO)
    sensor_server(args.listen_port).serve_forever()
