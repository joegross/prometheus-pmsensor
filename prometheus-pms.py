#!/usr/bin/env python3

import argparse
import logging
from collections import defaultdict

import serial
from prometheus_client import Gauge, start_http_server

logger = logging.getLogger(__name__)

DEFAULT_SERIAL = '/dev/cu.usbserial'
LISTEN_PORT = 8002
SAMPLES = 60


class sensor_server(object):
    def __init__(self, listen_port, serial_port, samples):
        self.serial_port = serial_port
        self.samples = samples
        start_http_server(listen_port)
        self.pms = Gauge('pms', 'PM Sensor ug/m3', ['serial_port', 'size'])
        self.port = serial.Serial(serial_port, baudrate=9600, timeout=2.0)

    def read_pm_line(self, port):
        rv = b''
        while True:
            ch1 = port.read()
            if ch1 == b'\x42':
                ch2 = port.read()
                if ch2 == b'\x4d':
                    rv += ch1 + ch2
                    rv += port.read(28)
                    return rv

    def post_data(self, res):
        for size, count in res.items():
            logging.debug("%s %s", size, count)
            self.pms.labels(serial_port=self.serial_port, size=size).set(count)

    def serve_forever(self):
        rollup = defaultdict(list)
        while True:
            rcv = self.read_pm_line(self.port)
            res = {
                # custom values
                'pm0.3': rcv[16] * 256 + rcv[17],
                'pm0.5': rcv[18] * 256 + rcv[19],
                'pm1.0': rcv[20] * 256 + rcv[21],
                'pm2.5': rcv[22] * 256 + rcv[23],
                'pm5.0': rcv[24] * 256 + rcv[25],
                'pm10.0': rcv[26] * 256 + rcv[27],
                # snippet values
                'apm10': rcv[4] * 256 + rcv[5],
                'apm25': rcv[6] * 256 + rcv[7],
                'apm100': rcv[8] * 256 + rcv[9],
                'pm10': rcv[10] * 256 + rcv[11],
                'pm25': rcv[12] * 256 + rcv[13],
                'pm100': rcv[14] * 256 + rcv[15],
                'gt03um': rcv[16] * 256 + rcv[17],
                'gt05um': rcv[18] * 256 + rcv[19],
                'gt10um': rcv[20] * 256 + rcv[21],
                'gt25um': rcv[22] * 256 + rcv[23],
                'gt50um': rcv[24] * 256 + rcv[25],
                'gt100um': rcv[26] * 256 + rcv[27]
                }
            for size, count in res.items():
                rollup[size].append(count)
                if len(rollup[size]) >= self.samples:
                    avg = float(sum(rollup[size])) / len(rollup[size])
                    logging.debug("%s %s", size, avg)
                    self.pms.labels(
                        serial_port=self.serial_port, size=size).set(avg)
                    rollup[size] = rollup[size][-self.samples:]


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
    parser.add_argument('-s', '--serial_port',
                        default=DEFAULT_SERIAL, help='serial port path')
    parser.add_argument('-p', '--listen_port',
                        default=LISTEN_PORT, help='listen port')
    parser.add_argument('-m', '--samples', default=SAMPLES, help='sample size')
    args = parser.parse_args()
    if args.verbose:
        init_logging(logging.DEBUG)
    else:
        init_logging(logging.INFO)
    sensor_server(args.listen_port, args.serial_port,
                  args.samples).serve_forever()
