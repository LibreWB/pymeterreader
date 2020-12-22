"""
Plain Reader
Created 2020.10.12 by Oliver Schwaneberg
"""
import re
from logging import debug, error
import typing as tp
import serial
from pymeterreader.device_lib.serial_reader import SerialReader
from pymeterreader.device_lib.common import Sample, strip


class PlainReader(SerialReader):
    """
    Polls meters with plain text output via
    EN 62056-21:2002 compliant optical interfaces.
    Tested with Landis+Gyr ULTRAHEAT T550 (UH50…)
    See https://en.wikipedia.org/wiki/IEC_62056
    """
    PROTOCOL = "PLAIN"
    __START_SEQ = b"/?!\x0D\x0A"

    def __init__(self, meter_id: str, tty: str, send_wakeup_zeros: int = 40, baudrate: int = 2400,
                 initial_baudrate: int = 300, **kwargs):
        """
        Initialize Plain Meter Reader object
        (See https://wiki.volkszaehler.org/software/obis for OBIS code mapping)
        :param meter_id: meter identification string (e.g. '12345678')
        :param tty: URL specifying the serial Port as required by pySerial serial_for_url()
        :param send_wakeup_zeros: number of zeros to send ahead of the request string
        :param initial_baudrate: Baudrate used to send the request
        :param baudrate: Baudrate used to read the answer
        """
        super().__init__(meter_id, tty, baudrate=baudrate, **kwargs)
        self.wakeup_zeros = send_wakeup_zeros
        self.initial_baudrate = initial_baudrate

    def poll(self) -> tp.Optional[Sample]:
        """
        Poll device
        :return: Sample, if successful
        """
        try:
            self.initialize_tty()
            # change baudrate
            self._tty_instance.baudrate = self.initial_baudrate
            # send wakeup string
            if self.wakeup_zeros:
                self._tty_instance.write(b"\x00" * self.wakeup_zeros)

            # send request message
            self._tty_instance.write(self.__START_SEQ)
            self._tty_instance.flush()

            # read identification message
            init_msg = self._tty_instance.readline()

            # change baudrate
            self._tty_instance.baudrate = self.baudrate
            response_bytes: bytes = self._tty_instance.readline()
            response = response_bytes.decode('utf-8')
            debug(f'Plain response: ({init_msg.decode("utf-8")})"{response}"')
            sample = self.__parse(response)
            if sample.meter_id is not None:
                return sample
        except UnicodeError as err:
            error(f'Decoding the Bytes as Unicode failed: {err}\n{response_bytes}')
        except serial.SerialException as err:
            error(f'Serial Interface error: {err}')
        return None

    def __parse(self, response: str) -> Sample:
        """
        Internal helper to extract relevant information
        :param response: decoded line
        """
        parsed = Sample()
        for ident, value, unit in re.findall(r"([\d.]+)\(([\d.]+)\*?([\w\d.]+)?\)", response):
            if not unit:
                if strip(self.meter_id) in value:
                    parsed.meter_id = value
            else:
                parsed.channels.append({'objName': ident,
                                        'value': float(value),
                                        'unit': unit})
        return parsed
