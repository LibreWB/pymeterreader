"""
SML Reader
Created 2020.10.12 by Oliver Schwaneberg
"""
from logging import debug, error, warning
import typing as tp
import serial
from sml import SmlBase
from pymeterreader.device_lib.serial_reader import SerialReader
from pymeterreader.device_lib.common import Sample, strip


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
        Poll device
        :return: Sample, if successful
        """
        try:
            self.initialize_tty()
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
                assert isinstance(sample,
                                  Sample), 'Parsing the Bytes with _parse() did not yield a Sample as second result!'
                if sample.meter_id is not None:
                    return sample
        except AssertionError as err:
            error(f'SML parsing failed: {err}')
        except serial.SerialException as err:
            error(f'Serial Interface error: {err}')
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
                sml_list = sml_frame['messageBody'].get('valList', [])
                for sml_entry in sml_list:
                    # Try reading the meter_id from sml entries without unit description and OBIS code for meter id
                    if 'unit' not in sml_entry and '1-0:0.0.9' in sml_entry.get('objName', ''):
                        read_meter_id = strip(str(sml_entry.get('value', '')))
                        if read_meter_id == self.meter_id:
                            parsed.meter_id = sml_entry.get('value')
                            break
                        else:
                            warning(f"Meter ID in SML frame {read_meter_id} does not match expected ID {self.meter_id}")
                if parsed.meter_id:
                    parsed.channels.extend(sml_list)
        return parsed
