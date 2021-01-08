"""
SML Reader
Created 2020.10.12 by Oliver Schwaneberg
"""
from logging import debug, error, warning
import typing as tp
import serial
from sml import SmlBase
from pymeterreader.device_lib.serial_reader import SerialReader
from pymeterreader.device_lib.common import Sample, strip, Device


class SmlReader(SerialReader):
    """
    Reads meters with SML output via
    EN 62056-21:2002 compliant optical interfaces.
    Tested with EMH eHZ electrical meters
    See https://en.wikipedia.org/wiki/IEC_62056
    """
    PROTOCOL = "SML"
    __START_SEQ = b'\x1b\x1b\x1b\x1b\x01\x01\x01\x01'
    __END_SEQ = b'\x1b\x1b\x1b\x1b'

    def __init__(self, meter_id: str, tty: str, **kwargs):
        """
        Initialize SML Meter Reader object
        (See https://wiki.volkszaehler.org/software/obis for OBIS code mapping)
        :param meter_id: meter identification string (e.g. '1 EMH00 12345678')
        :param tty: URL specifying the serial Port as required by pySerial serial_for_url()
        :kwargs: parameters for the SerialReader superclass
        """
        super().__init__(meter_id, tty, **kwargs)

    def poll(self) -> tp.Optional[Sample]:
        """
        Public method for polling a Sample from the meter. Enforces that the meter_id matches.
        :return: Sample, if successful
        """
        sample: Sample = self.__fetch_sample()
        if sample:
            if sample.meter_id == self.meter_id:
                return sample
            else:
                warning(f"Meter ID in SML frame {sample.meter_id} does not match expected ID {self.meter_id}")
        return None

    def __fetch_sample(self) -> tp.Optional[Sample]:
        """
        Try to retrieve a Sample from any connected meter with the current configuration
        :return: Sample, if successful
        """
        try:
            self.initialize_tty()
            # Open, Use and Close tty_instance
            with self._tty_instance:
                # Flush input buffer if more than 2 SML messages(~ 800 Bytes) are already in the buffer
                if self._tty_instance.in_waiting > 800:
                    self._tty_instance.reset_input_buffer()
                    debug("Flushed Input buffer")
                # Discard Data until finding a Start Sequence in the buffer
                self._tty_instance.read_until(expected=self.__START_SEQ)
                # Read Data up to End Sequence
                payload = self._tty_instance.read_until(expected=self.__END_SEQ)
                # Read the four subsequent Bytes(Checksum+Number of Fill Bytes)
                trailer = self._tty_instance.read(4)
            # Reconstruct original SML Structure by combining the extracted sections
            sml_reconstructed = self.__START_SEQ + payload + trailer
            # Test if SML Start is well formatted
            assert sml_reconstructed.startswith(
                self.__START_SEQ), 'Reconstructed SML sequence has malformed Start Sequence!'
            # Test if SML End Sequence is present
            assert sml_reconstructed[8:-4].endswith(
                self.__END_SEQ), 'Reconstructed SML sequence has malformed End Sequence!'
            frame = SmlBase.parse_frame(sml_reconstructed)
            if len(frame) == 2:
                sample = self.__parse(frame[1])
                assert isinstance(sample, Sample), 'Parsing the SML frame did not yield a Sample!'
                return sample
        except AssertionError as err:
            error(f'SML parsing failed: {err}')
        except serial.SerialException as err:
            error(f'Serial Interface error: {err}')
        return None

    @staticmethod
    def detect(tty_regex: str = None, **kwargs) -> tp.List[Device]:
        # Instantiate Reader of and call SerialReader.detect_serial_devices()
        # pylint: disable=W0212
        return SmlReader("unknown", "loop://", **kwargs)._detect_serial_devices(tty_regex=tty_regex)

    def _discover(self) -> tp.Optional[Device]:
        """
        Returns a Device if the class extending SerialReader can discover a meter with the configured settings
        """
        sample: Sample = self.__fetch_sample()
        if sample:
            return Device(sample.meter_id, self.tty_url, self.PROTOCOL, sample.channels)
        else:
            return None

    def __parse(self, sml_frame: tp.Union[list, dict], parsed=None) -> Sample:
        """
        Internal helper to extract relevant information
        :param sml_frame: sml data from parser
        :param parsed: only for recursive object reference forwarding
        """
        if parsed is None:
            parsed = Sample()
        if isinstance(sml_frame, list):
            for elem in sml_frame:
                self.__parse(elem, parsed)
        elif isinstance(sml_frame, dict):
            if 'messageBody' in sml_frame:
                var_list = sml_frame['messageBody'].get('valList', [])
                for variable in var_list:
                    if 'unit' not in variable and strip(self.meter_id) in strip(str(variable.get('value', ''))):
                        parsed.meter_id = variable.get('value')
                        break
                if parsed.meter_id:
                    parsed.channels.extend(var_list)
        return parsed
