#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''BTHome v2 sensor constants (from https://bthome.io/format/)
    describes all available sensor types.'''



# ##############################################################################
from dataclasses import dataclass, field
# ##############################################################################



# ##############################################################################
@dataclass
class SensorData:
  '''Class describing any BTHome sensor'''
  property: str = ''      # name of property
  bytes: int = 1          # # of data bytes, 0 means variable, stated next
  signed: bool = False    # signed data or unsigned?
  factor: float = 1.0     # multiplying factor
  unit: str | None = None # unit
  binary: bool = False    # is sensor binary?
  # event sensors contain an integer-indexed dict of available events
  events: dict[int, str | None] = field(default_factory=lambda: ({}))
#: endclass SensorData  ########################################################



# ##############################################################################
# description of all available sensor measurements
SENSOR: dict[int, SensorData] = {
  0x00: SensorData(
    property = 'packet id'
  ),
  0x01: SensorData(
    property = 'battery',
    unit = '%'
  ),
  0x02: SensorData(
    property = 'temperature',
    bytes = 2,
    signed = True,
    factor = 0.01,
    unit = '°C'
  ),
  0x03: SensorData(
    property = 'humidity',
    bytes = 2,
    factor = 0.01,
    unit = '%'
  ),
  0x04: SensorData(
    property = 'pressure',
    bytes = 3,
    factor = 0.01,
    unit = 'hPa'
  ),
  0x05: SensorData(
    property = 'illuminance',
    bytes = 3,
    factor = 0.01,
    unit = 'lux'
  ),
  0x06: SensorData(
    property = 'mass (kg)',
    bytes = 2,
    factor = 0.01,
    unit = 'kg'
  ),
  0x07: SensorData(
    property = 'mass (lb)',
    bytes = 2,
    factor = 0.01,
    unit = 'lb'
  ),
  0x08: SensorData(
    property = 'dewpoint',
    bytes = 2,
    signed = True,
    factor = 0.01,
    unit = '°C'
  ),
  0x09: SensorData(
    property = 'count'
  ),
  0x0A: SensorData(
    property = 'energy',
    bytes = 3,
    factor = 0.001,
    unit = 'kWh'
  ),
  0x0B: SensorData(
    property = 'power',
    bytes = 3,
    factor = 0.01,
    unit = 'W'
  ),
  0x0C: SensorData(
    property = 'voltage',
    bytes = 2,
    factor = 0.001,
    unit = 'V'
  ),
  0x0D: SensorData(
    property = 'pm2.5',
    bytes = 2,
    unit = 'ug/m3'
  ),
  0x0E: SensorData(
    property = 'pm10',
    bytes = 2,
    unit = 'ug/m3'
  ),
  0x0F: SensorData(
    property = 'generic boolean',
    binary = True
  ),
  0x10: SensorData(
    property = 'power',
    binary = True
  ),
  0x11: SensorData(
    property = 'opening',
    binary = True
  ),
  0x12: SensorData(
    property = 'co2',
    bytes = 2,
    unit = 'ppm'
  ),
  0x13: SensorData(
    property = 'tvoc',
    bytes = 2,
    unit = 'ug/m3'
  ),
  0x14: SensorData(
    property = 'moisture',
    bytes = 2,
    factor = 0.01,
    unit = '%'
  ),
  0x15: SensorData(
    property = 'battery',
    binary = True
  ),
  0x16: SensorData(
    property = 'battery charging',
    binary = True
  ),
  0x17: SensorData(
    property = 'carbon monoxide',
    binary = True
  ),
  0x18: SensorData(
    property = 'cold',
    binary = True
  ),
  0x19: SensorData(
    property = 'connectivity',
    binary = True
  ),
  0x1A: SensorData(
    property = 'door',
    binary = True
  ),
  0x1B: SensorData(
    property = 'garage door',
    binary = True
  ),
  0x1C: SensorData(
    property = 'gas',
    binary = True
  ),
  0x1D: SensorData(
    property = 'heat',
    binary = True
  ),
  0x1E: SensorData(
    property = 'light',
    binary = True
  ),
  0x1F: SensorData(
    property = 'lock',
    binary = True
  ),
  0x20: SensorData(
    property = 'moisture',
    binary = True
  ),
  0x21: SensorData(
    property = 'motion',
    binary = True
  ),
  0x22: SensorData(
    property = 'moving',
    binary = True
  ),
  0x23: SensorData(
    property = 'occupancy',
    binary = True
  ),
  0x24: SensorData(
    property = 'plug',
    binary = True
  ),
  0x25: SensorData(
    property = 'presence',
    binary = True
  ),
  0x26: SensorData(
    property = 'problem',
    binary = True
  ),
  0x27: SensorData(
    property = 'running',
    binary = True
  ),
  0x28: SensorData(
    property = 'safety',
    binary = True
  ),
  0x29: SensorData(
    property = 'smoke',
    binary = True
  ),
  0x2A: SensorData(
    property = 'sound',
    binary = True
  ),
  0x2B: SensorData(
    property = 'tamper',
    binary = True
  ),
  0x2C: SensorData(
    property = 'vibration',
    binary = True
  ),
  0x2D: SensorData(
    property = 'window',
    binary = True
  ),
  0x2E: SensorData(
    property = 'humidity',
    unit = '%'
  ),
  0x2F: SensorData(
    property = 'moisture',
    unit = '%'
  ),
  0x3A: SensorData(
    property = 'button',
    events = {
      0x00: None,
      0x01: 'press',
      0x02: 'double_press',
      0x03: 'triple_press',
      0x04: 'long_press',
      0x05: 'long_double_press',
      0x06: 'long_triple_press',
      0x80: 'hold_press'
    }
  ),
  0x3C: SensorData(
    property = 'dimmer',
    bytes = 2,
    events = {
      0x00: None,
      0x01: 'rotate_left',
      0x02: 'rotate_right'
    }
  ),
  0x3D: SensorData(
    property = 'count',
    bytes = 2
  ),
  0x3E: SensorData(
    property = 'count',
    bytes = 4
  ),
  0x3F: SensorData(
    property = 'rotation',
    bytes = 2,
    signed = True,
    factor = 0.1,
    unit = '°'
  ),
  0x40: SensorData(
    property = 'distance (mm)',
    bytes = 2,
    unit = 'mm'
  ),
  0x41: SensorData(
    property = 'distance (m)',
    bytes = 2,
    factor = 0.1,
    unit = 'm'
  ),
  0x42: SensorData(
    property = 'duration',
    bytes = 3,
    factor = 0.001,
    unit = 's'
  ),
  0x43: SensorData(
    property = 'current',
    bytes = 2,
    factor = 0.001,
    unit = 'A'
  ),
  0x44: SensorData(
    property = 'speed',
    bytes = 2,
    factor = 0.01,
    unit = 'm/s'
  ),
  0x45: SensorData(
    property = 'temperature',
    bytes = 2,
    signed = True,
    factor = 0.1,
    unit = '°C'
  ),
  0x46: SensorData(
    property = 'UV index',
    factor = 0.1
  ),
  0x47: SensorData(
    property = 'volume',
    bytes = 2,
    factor = 0.1,
    unit = 'L'
  ),
  0x48: SensorData(
    property = 'volume',
    bytes = 2,
    unit = 'mL'
  ),
  0x49: SensorData(
    property = 'volume flow rate',
    bytes = 2,
    factor = 0.001,
    unit = 'm3/hr'
  ),
  0x4A: SensorData(
    property = 'voltage',
    bytes = 2,
    factor = 0.1,
    unit = 'V'
  ),
  0x4B: SensorData(
    property = 'gas',
    bytes = 3,
    factor = 0.001,
    unit = 'm3'
  ),
  0x4C: SensorData(
    property = 'gas',
    bytes = 4,
    factor = 0.001,
    unit = 'm3'
  ),
  0x4D: SensorData(
    property = 'energy',
    bytes = 4,
    factor = 0.001,
    unit = 'kWh'
  ),
  0x4E: SensorData(
    property = 'volume',
    bytes = 4,
    factor = 0.001,
    unit = 'L'
  ),
  0x4F: SensorData(
    property = 'water',
    bytes = 4,
    factor = 0.001,
    unit = 'L'
  ),
  0x50: SensorData(
    property = 'timestamp',
    bytes = 4
  ),
  0x51: SensorData(
    property = 'acceleration',
    bytes = 2,
    factor = 0.001,
    unit = 'm/s²'
  ),
  0x52: SensorData(
    property = 'gyroscope',
    bytes = 2,
    factor = 0.001,
    unit = '°/s'
  ),
  0x53: SensorData(
    property = 'text',
    bytes = 0
  ),
  0x54: SensorData(
    property = 'raw',
    bytes = 0
  ),
  0x55: SensorData(
    property = 'volume storage',
    bytes = 4,
    factor = 0.001,
    unit = 'L'
  ),
  0x56: SensorData(
    property = 'conductivity',
    bytes = 2,
    unit = 'µS/cm'
  ),
  0x57: SensorData(
    property = 'temperature',
    signed = True,
    unit = '°C'
  ),
  0x58: SensorData(
    property = 'temperature',
    signed = True,
    factor = 0.35,
    unit = '°C'
  ),
  0x59: SensorData(
    property = 'count',
    signed = True
  ),
  0x5A: SensorData(
    property = 'count',
    bytes = 2,
    signed = True
  ),
  0x5B: SensorData(
    property = 'count',
    bytes = 4,
    signed = True
  ),
  0x5C: SensorData(
    property = 'power',
    bytes = 4,
    signed = True,
    factor = 0.01,
    unit = 'W'
  ),
  0x5D: SensorData(
    property = 'current',
    bytes = 2,
    signed = True,
    factor = 0.001,
    unit = 'A'
  ),
  0xF0: SensorData(
    property = 'device type id',
    bytes = 2
  ),
  0xF1: SensorData(
    property = 'firmware version',
    bytes = 4
  ),
  0xF2: SensorData(
    property = 'firmware version',
    bytes = 3
  )
} # ############################################################################
