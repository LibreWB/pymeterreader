"""
Commmon code for all readers
"""
from dataclasses import dataclass, field
from time import time
import typing as tp
from string import digits, ascii_letters, punctuation
legal_characters = digits + ascii_letters + punctuation


@dataclass(frozen=True)
class Channel:
    """
    Data storage object to represent a channel
    """
    channel_name: str
    value: tp.Union[str, int, float]
    unit: str = None


@dataclass()
class Sample:
    """
    Data storage object to represent a readout
    """
    time: float = time()
    meter_id: str = None
    channels: tp.List[Channel] = field(default_factory=list)


class Device:
    """
    Representation of a device
    """
    def __init__(self, identifier: str = "", tty: str = "", protocol: str = "",
                 channels: tp.Optional[tp.Dict[str, tp.Tuple[str, str]]] = None):
        self.identifier = identifier
        self.tty = tty
        self.protocol = protocol
        self.channels = channels if channels is not None else {}


def strip(string: str) -> str:
    """
    Strip irrelevant characters from identifiaction
    :rtype: object
    :param string: original string
    :return: stripped string
    """
    return ''.join([char for char in string if char in legal_characters]).strip().upper()
