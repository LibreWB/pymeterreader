"""
Base Reader (ABC)
Created 2020.10.12 by Oliver Schwaneberg
"""
import typing as tp
from abc import ABC, abstractmethod
from logging import warning
from pymeterreader.device_lib.common import Sample


class BaseReader(ABC):
    """
    Implementation Base for a Meter Protocol
    """
    PROTOCOL = "ABSTRACT"

    @abstractmethod
    def __init__(self, meter_id: tp.Union[str, int], **kwargs):
        """
        Initialize Meter Reader object
        :param meter_id: meter identification string (e.g. '1 EMH00 12345678')
        :kwargs: implementation specific parameters
        """
        self.meter_id = meter_id
        if kwargs:
            warning(f'Unknown parameter{"s" if len(kwargs) > 1 else ""}:'
                    f' {", ".join(kwargs.keys())}')

    @abstractmethod
    def poll(self) -> tp.Optional[Sample]:
        """
        Poll the reader and retrieve a new sample
        :return: Sample, if successful else None
        """
        raise NotImplementedError("This is just an abstract class.")
