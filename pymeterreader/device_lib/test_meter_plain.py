import unittest
from unittest import mock
from unittest.mock import DEFAULT, MagicMock, PropertyMock

import serial
from serial import serial_for_url
from serial.tools.list_ports_common import ListPortInfo
from pymeterreader.device_lib import PlainReader
from pymeterreader.device_lib.common import Channel, Device
from pymeterreader.device_lib.test_meter import StaticMeterSimulator, SerialTestData


class PlainMeterSimulator(StaticMeterSimulator):
    """
    Simulate a Plain Meter that requires a wakeup before sending a sample.
    This implementation is not compatible with a loop:// interface since it depends on having different send/receiver buffers.
    """

    def __init__(self) -> None:
        start_sequence = b'\x1b\x1b\x1b\x1b\x01\x01\x01\x01'
        test_frame = b'\x026.8(0006047*kWh)6.26(00428.35*m3)9.21(99999999)\r\n'
        test_data = SerialTestData(
            start_sequence + test_frame,
            identifier='1 EMH 00 4921570',
            channels=[Channel(channel_name='129-129:199.130.3*255', value='EMH', unit=None),
                      Channel(channel_name='1-0:1.8.0*255', value=27400268.6, unit='Wh'),
                      Channel(channel_name='1-0:2.8.0*255', value=18929944.0, unit='Wh'),
                      Channel(channel_name='1-0:1.8.1*255', value=27400268.6, unit='Wh'),
                      Channel(channel_name='1-0:2.8.1*255', value=18929944.0, unit='Wh'),
                      Channel(channel_name='1-0:1.8.2*255', value=0, unit='Wh'),
                      Channel(channel_name='1-0:2.8.2*255', value=0, unit='Wh'),
                      Channel(channel_name='1-0:16.7.0*255', value=-307.8, unit='W'),
                      Channel(channel_name='129-129:199.130.5*255',
                              value='58af289a611352984cf85295237ef26670cb3d367e218b48d952789fc4a5888604012b323490ced3d96d341c9e9ccf77',
                              unit=None)])
        super().__init__(test_data)

    def wait_for_wakeup(self) -> None:
        wakeup_counter = 0
        wakeup_sequence = b"\x00"
        # Loop until we have received the wakeup sequence
        while wakeup_counter < 40:
            try:
                if self.tty.read(1) == wakeup_sequence:
                    wakeup_counter += 1
                else:
                    # Reset counter if the sequence is interrupted
                    wakeup_counter = 0
            # Keep trying even when the serial port has not been opened or has already been closed by the reader
            except serial.PortNotOpenError:
                pass
        # Read start sequence
        start_sequence = b"/?!\x0D\x0A"
        # Block until start sequence length has been read
        sequence = self.tty.read(len(start_sequence))
        # Return whether the start_sequence has been received
        return sequence == start_sequence


class TestPlainReader(unittest.TestCase):
    @mock.patch('serial.serial_for_url', autospec=True)
    def test_init(self, serial_for_url_mock):
        # Create shared serial instance with unmocked import
        shared_serial_instance = serial_for_url("loop://", baudrate=9600, timeout=5)
        serial_for_url_mock.return_value = shared_serial_instance
        simulator = PlainMeterSimulator()
        simulator.start()
        reader = PlainReader("1EMH004921570", "loop://")
        sample = reader.poll()
        simulator.stop()
        self.assertEqual(sample.meter_id, simulator.get_meter_id())
        self.assertEqual(sample.channels, simulator.get_channels())
        return

    def test_init_fail(self):
        reader = PlainReader("1EMH004921570", "loop://")
        sample = reader.poll()
        self.assertIsNone(sample)

    @mock.patch('serial.tools.list_ports.grep', autospec=True)
    @mock.patch('serial.serial_for_url', autospec=True)
    def test_detect(self, serial_for_url_mock, list_ports_mock):
        # Make list_ports_mock an instance variable
        self.list_ports_mock = list_ports_mock
        # Create Mock for ListPortInfo
        list_port_mock = MagicMock()
        device_property = PropertyMock(return_value="/dev/ttyUSB1")
        # Add Sideeffect that starts the SmlSimulator once the device property is accessed
        device_property.side_effect = self.start_simulator
        # Attach property to Mock
        type(list_port_mock).device = device_property
        list_ports_mock.return_value = [ListPortInfo("/dev/ttyUSB0"), list_port_mock]
        # Create shared serial instance with unmocked import
        shared_serial_instance = serial_for_url("loop://", baudrate=9600, timeout=5)
        serial_for_url_mock.return_value = shared_serial_instance
        # Create SmlSimulator that will be started on the second call to the list_ports_mock
        self.simulator = PlainMeterSimulator()
        # Start device detection
        devices = PlainReader("irrelevent", "unused://").detect()
        self.assertEqual(len(devices), 1)
        self.assertIn(Device(self.simulator.get_meter_id(), '/dev/ttyUSB1', 'PLAIN', self.simulator.get_channels()),
                      devices)

    def start_simulator(self) -> DEFAULT:
        self.simulator.start()
        return DEFAULT


if __name__ == '__main__':
    unittest.main()
