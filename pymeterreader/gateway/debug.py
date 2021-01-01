"""
Uploader that prints to the Console instead of uploading
"""
import typing as tp
from logging import getLogger, debug
from pymeterreader.gateway import BaseGateway


class DebugGateway(BaseGateway):
    """
    This class is used for debugging uploads to a middleware
    """
    def __init__(self):
        super().__init__()
        getLogger(__name__)
        self.post_timestamps = {}

    def post(self, uuid: str, value: tp.Union[int, float], timestamp: int) -> bool:
        timestamp = self.timestamp_to_int(timestamp)
        self.post_timestamps[uuid] = timestamp, value
        debug(f"Sent Channel {uuid} @ {timestamp}={value}")
        return True

    def get(self, uuid: str) -> tp.Optional[tp.Tuple[int, tp.Union[int, float]]]:
        timestamp, value = self.post_timestamps.get(uuid, (0, 0))
        debug(f"Received Channel {uuid} @ {timestamp}={value}")
        return timestamp, 0
