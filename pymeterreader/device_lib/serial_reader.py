"""
Serial Reader (BaseReader)
"""
import typing as tp
from abc import abstractmethod
from logging import warning, info, error
import serial
import serial.tools.list_ports
from pymeterreader.device_lib.common import Device
from pymeterreader.device_lib.base import BaseReader


class SerialReader(BaseReader):
    """"
    Implementation Base for Meter Protocols that utilize a Serial Connection
    """

    @abstractmethod
    def __init__(self, meter_id: tp.Union[str, int], tty: str, parity: str = "None", baudrate: int = 9600,
                 bytesize: int = 8, stopbits: int = 1, timeout: int = 5, **kwargs):
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
        super().__init__(meter_id, **kwargs)
        self.tty_url = tty
        self._tty_instance = None
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.stopbits = stopbits
        self.timeout = timeout
        self.parity = serial.PARITY_NONE
        if 'EVEN' in parity:
            self.parity = serial.PARITY_EVEN
        elif 'ODD' in parity:
            self.parity = serial.PARITY_ODD

    def initialize_tty(self, do_not_open: bool = True) -> None:
        """
        Initialize serial instance if it is uninitialized
        """
        if self._tty_instance is None:
            if self.tty_url.startswith("hwgrep://"):
                warning("Relying on hwgrep for Serial port identification is not recommended!")
            self._tty_instance = serial.serial_for_url(self.tty_url,
                                                       baudrate=self.baudrate,
                                                       bytesize=self.bytesize,
                                                       parity=self.parity,
                                                       stopbits=self.stopbits,
                                                       timeout=self.timeout,
                                                       do_not_open=do_not_open)

    def close_tty(self) -> None:
        """
        Close Serial Connection
        """
        self._tty_instance.close()
        self._tty_instance = None

    def _detect_serial_devices(self, tty_regex: str = ".*", **kwargs) -> tp.List[Device]:
        """
        Test all available serial ports for a meter of the SerialReader implementation
        :param tty_regex: Regex to filter the output from serial.tools.list_ports()
        :kwargs: parameters that are passed to the SerialReader implementation that is instantiated to test every port
        """
        devices: tp.List[Device] = []
        # Test all matching tty ports
        for possible_port_info in serial.tools.list_ports.grep(tty_regex):
            try:
                discovered_tty_url = possible_port_info.device
                # Create new Instance of the current SerialReader implementation
                # This ensures that the internal state is reset for every discovery
                serial_reader_implementation = self.__class__("irrelevant", discovered_tty_url, **kwargs)
                # Utilize SubClass._discover() to handle implementation specific discovery
                device = serial_reader_implementation._discover()
                if device:
                    devices.append(device)
                else:
                    info(f"No {serial_reader_implementation.PROTOCOL} Meter found at {discovered_tty_url}")
            except Exception as err:
                error(f"Uncaught Exception while tyring to detect {serial_reader_implementation.PROTOCOL} Meter!"
                      " Please report this to the developers.")
                raise err
        return devices

    @abstractmethod
    def _discover(self) -> tp.Optional[Device]:
        """
        Returns a Device if the class extending SerialReader can discover a meter with the configured settings
        """
        raise NotImplementedError("This is just an abstract class.")
