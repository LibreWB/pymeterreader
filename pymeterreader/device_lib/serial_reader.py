"""
Serial Reader (BaseReader)
"""
import typing as tp
import serial
from abc import abstractmethod
from pymeterreader.device_lib.base import BaseReader


class SerialReader(BaseReader):
    """"
    Implementation Base for Meter Protocols that utilize a Serial Connection
    """

    @abstractmethod
    def __init__(self, meter_id: tp.Union[str, int], tty: str, parity: str = "None", baudrate: int = 9600, bytesize: int = 8,
                 stopbits=1, **kwargs):
        """
        Initialize Meter Reader object
        :param meter_id: meter identification string (e.g. '1 EMH00 12345678')
        :param tty: URL specifying the serial Port as required by pySerial serial_for_url()
        :baudrate: serial baudrate, defaults to 9600
        :bytesize: word size on serial port (Default: 8)
        :parity: serial parity, EVEN, ODD or NONE (Default: NONE)
        :stopbits: Number of stopbits (Default: 1)
        :kwargs: unparsed parameters
        """
        super().__init__(meter_id,**kwargs)
        self.tty_url = tty
        self._tty_instance = None
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.stopbits = stopbits
        self.parity = serial.PARITY_NONE
        if 'EVEN' in parity:
            self.parity = serial.PARITY_EVEN
        elif 'ODD' in parity:
            self.parity = serial.PARITY_ODD

    def initialize_tty(self) -> None:
        """
        Initialize serial instance if it is uninitialized
        """
        if self._tty_instance is None:
            self._tty_instance = serial.serial_for_url(self.tty_url,
                                                       baudrate=self.baudrate,
                                                       bytesize=self.bytesize,
                                                       parity=self.parity,
                                                       stopbits=self.stopbits,
                                                       timeout=5)

    def close_tty(self) -> None:
        """
        Close Serial Connection
        """
        self._tty_instance.close()
        self._tty_instance = None
