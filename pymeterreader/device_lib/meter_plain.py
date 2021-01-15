"""
Plain Reader
Created 2020.10.12 by Oliver Schwaneberg
"""
import os
import re
from logging import info, debug, error, warning
import typing as tp
import serial
from threading import Lock
from pymeterreader.device_lib.base import BaseReader
from pymeterreader.device_lib.common import Sample, Device, strip, Channel
from pymeterreader.device_lib.serial_reader import SerialReader


class PlainReader(SerialReader):
    """
    Polls meters with plain text output via
    EN 62056-21:2002 compliant optical interfaces.
    Tested with Landis+Gyr ULTRAHEAT T550 (UH50…)
    See https://en.wikipedia.org/wiki/IEC_62056
    """
    PROTOCOL = "PLAIN"
    __START_SEQ = b"/?!\x0D\x0A"

    def __init__(self, meter_id: str, tty: str, send_wakeup_zeros: int = 40, initial_baudrate: int = 300,
                 baudrate: int = 2400, **kwargs):
        """
        Initialize Plain Meter Reader object
        (See https://wiki.volkszaehler.org/software/obis for OBIS code mapping)
        :param meter_id: meter identification string (e.g. '1 EMH00 12345678')
        :param tty: URL specifying the serial Port as required by pySerial serial_for_url()
        :param send_wakeup_zeros: number of zeros to send ahead of the request string
        :param initial_baudrate: Baudrate used to send the request
        :param baudrate: Baudrate used to read the answer
        :kwargs: parameters for the SerialReader superclass
        """
        super().__init__(meter_id, tty, baudrate=initial_baudrate, **kwargs)
        self.wakeup_zeros = send_wakeup_zeros
        self.__initial_baudrate = initial_baudrate
        self.__baudrate = baudrate

    def poll(self) -> tp.Optional[Sample]:
        """
        Public method for polling a Sample from the meter. Enforces that the meter_id matches.
        :return: Sample, if successful
        """
        sample: Sample = self.__fetch_sample()
        if sample:
            if strip(self.meter_id) in strip(sample.meter_id):
                return sample
            else:
                warning(f"Meter ID in frame {sample.meter_id} does not match expected ID {self.meter_id}")
        return None

    def __fetch_sample(self) -> tp.Optional[Sample]:
        """
        Try to retrieve a Sample from any connected meter with the current configuration
        :return: Sample, if successful
        """
        try:
            self.initialize_tty()
            with self._tty_instance as tty:
                # Send wakeup Sequence
                if self.wakeup_zeros > 0:
                    # Set wakeup baudrate
                    tty.baudrate = self.__initial_baudrate
                    # Send wakeup sequence
                    tty.write(b"\x00" * self.wakeup_zeros)
                    # Send request message
                    tty.write(self.__START_SEQ)
                    # Clear send buffer
                    tty.flush()
                    # Read identification message
                    init_bytes: bytes = self._tty_instance.readline()
                # Change baudrate to higher speed
                tty.baudrate = self.__baudrate
                # Read response
                response_bytes: bytes = tty.readline()
            # Decode response
            init: str = init_bytes.decode('utf-8')
            response: str = response_bytes.decode('utf-8')
            debug(f'Plain response: ({init}){response}')
            sample = self.__parse(response)
            assert isinstance(sample, Sample), 'Parsing the response did not yield a Sample!'
            return sample
        except UnicodeError as err:
            error(f'Decoding the Bytes as Unicode failed: {err}\n{response_bytes}')
        except AssertionError as err:
            error(f'Parsing failed: {err}')
        except serial.SerialException as err:
            error(f'Serial Interface error: {err}')
        return None


    @staticmethod
    def detect(tty=r'ttyUSB\d+', **kwargs) -> tp.List[Device]:
        devices: tp.List[Device] = []
        sp = os.path.sep
        used_interfaces = [device.tty for device in devices]
        potential_ttys = [f'{sp}dev{sp}{file_name}'
                          for file_name in os.listdir(f'{sp}dev{sp}')
                          if re.match(tty, file_name)
                          and f'{sp}dev{sp}{file_name}' not in used_interfaces]
        for tty_path in potential_ttys:
            response = PlainReader.__get_response(tty_path)
            channels: tp.List[Channel] = []
            if response:
                for ident, value, unit in re.findall(r"([\d.]+)\(([\d.]+)\*?([\w\d.]+)?\)", response):
                    identifier = None
                    if not unit:
                        identifier = value
                    else:
                        channels.append(Channel(ident, value, unit))
                if identifier:
                    device = Device(identifier,
                                    tty_path,
                                    'plain',
                                    channels)
                    devices.append(device)
        return devices

    def _discover(self) -> tp.Optional[Device]:
        pass

    def __parse(self, response: str) -> tp.Optional[Sample]:
        """
        Internal helper to extract relevant information
        :param response: decoded line
        """
        parsed = None
        for ident, value, unit in re.findall(r"([\d.]+)\(([\d.]+)\*?([\w\d.]+)?\)", response):
            if not parsed:
                parsed = Sample()
            if not unit and ident == '9.21':
                parsed.meter_id = value
            else:
                parsed.channels.append(Channel(ident, float(value), unit))
        return parsed
