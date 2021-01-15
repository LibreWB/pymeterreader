import typing as tp
from abc import abstractmethod
from dataclasses import dataclass, field
from threading import Thread
from time import sleep
import serial

from pymeterreader.device_lib.common import Channel


@dataclass(frozen=True)
class SerialTestData:
    binary: bytes
    identifier: str
    channels: tp.List[Channel] = field(default_factory=list)


class MeterSimulator(Thread):
    """
    Simulate Meter that sends a measurement
    """

    def __init__(self, sleep_interval: float) -> None:
        self.__continue = True
        self.sleep_interval = sleep_interval
        # Open the shared serial instance using the mocked serial.serial_for_url function
        self.tty = serial.serial_for_url("loop://")
        super().__init__()

    def run(self) -> None:
        # Try to write continuously
        while self.__continue:
            self.wait_for_wakeup()
            try:
                self.tty.write(self.get_sample_bytes())
            # Keep trying even when the serial port has not been opened or has already been closed by the reader
            except serial.PortNotOpenError:
                pass
            # Send next measurement after sleep interval. Time drift depends on this functions runtime
            sleep(self.sleep_interval)

    def stop(self):
        self.__continue = False

    def wait_for_wakeup(self) -> None:
        """
        This method blocks until the wakeup sequence is received. The default implementation returns immediately.
        """
        return

    @abstractmethod
    def get_sample_bytes(self) -> bytes:
        raise NotImplementedError("This is just an abstract class.")

    @abstractmethod
    def get_meter_id(self) -> str:
        raise NotImplementedError("This is just an abstract class.")

    @abstractmethod
    def get_channels(self) -> tp.List[Channel]:
        raise NotImplementedError("This is just an abstract class.")


class StaticMeterSimulator(MeterSimulator):
    def __init__(self, test_data: SerialTestData, sleep_interval: float = 0.5) -> None:
        super().__init__(sleep_interval)
        self.__test_data = test_data

    def get_sample_bytes(self) -> bytes:
        return self.__test_data.binary

    def get_meter_id(self) -> str:
        return self.__test_data.identifier

    def get_channels(self) -> tp.List[Channel]:
        return self.__test_data.channels
