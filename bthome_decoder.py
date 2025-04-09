#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''Manage BTHome v2 protocol and publish advertisements to MQTT brokers.'''



# ##############################################################################
import  re
from    dataclasses import dataclass, field
import  logging as lg
from    time import time
from    copy import deepcopy
import  ssl
import  asyncio
import  json
# ..............................................................................
import  yaml                                # pyyaml + types-PyYAML
from    Cryptodome.Cipher import AES        # pycryptodome[x]
import  aiomqtt                             # aiomqtt
# ..............................................................................
from    bthome_constants import SENSOR
# ##############################################################################



# some constants  ##############################################################
# matches the BLE BTHome data UUID
_BTHOME_UUID = 'fcd2'
# timeouts
_AIOMQTT_TIMEOUT = 10  # s
try:
  import  certifi                           # certifi needed on MSYS2
  _CAFILE: str | None = certifi.where()
except ImportError:
  _CAFILE = None
#: endtry
# matches one or more slashes
_SLASHES_RE = re.compile('/+')
# ##############################################################################



@dataclass  # ##################################################################
class Broker:
  '''Class describing an MQTT broker where to publish to'''
  hostname: str = '127.0.0.1'
  port: int = 8883
  user: str = ''
  password: str = ''
  encrypt: bool = True
  insecure: bool = False  # true to accept invalid certificates
  topics: list[str] = field(default_factory=lambda: ([]))
# endclass Broker ##############################################################



@dataclass  # ##################################################################
class BTHomeDevice:
  '''Class describing a BTHome v2 device'''
  mac: str = ''             # BLE device MAC address
  key: bytes = b''          # decryption key
  deduplicate: bool = True  # accept (False) or not duplicated packets
  # brokers where to publish measurements
  brokers: list[Broker] = field(default_factory=lambda: ([]))
  counter: int = -1         # AES decryption counter
  ciphertext: bytes = b''   # last valid ciphertext
  payload: bytes = b''      # last valid payload
  packet_id: int = -1       # last packet ID
  timestamp: float = 0.0    # timestamp of last valid payload
  promiscuous: bool = False # device added in promiscuous mode (True)


  # ****************************************************************************
  def decrypt(self, ciphertext: bytes) -> bool:
    '''Decrypts a BTHome v2 encrypted payload. Returns True on success'''
    lg.debug('%s', f'Decrypting ciphertext "{ciphertext!r}" for device "{self.mac}".')
    if len(ciphertext) <= 9:
      lg.warning('%s', f'Ciphertext "{ciphertext!r}" for device "{self.mac}" too short.')
      return False
    #: endif
    if self.key == b'':
      lg.warning('%s', f'Decryption key not specified for device {self.mac}.')
      return False
    #: endif
    if self.deduplicate and self.ciphertext == ciphertext:
      lg.debug('%s', f'Skipping duplicated ciphertext for device {self.mac}.')
      return False
    #: endif
    new_counter_b = ciphertext[-8:-4]
    new_counter = int.from_bytes(new_counter_b, byteorder='little', signed=False)
    # protect against replay attacks
    if ((0x100 <= new_counter < self.counter)
        and (self.ciphertext != b'')):
      lg.warning('%s', f'Encrypted packet rejected for device "{self.mac}" (decreasing counter).')
      return False
    #: endif
    nonce = bytes.fromhex(self.mac) + b'\xd2\xfc' + ciphertext[0:1] + new_counter_b
    mic = ciphertext[-4:]
    cipher = AES.new(self.key, AES.MODE_CCM, nonce=nonce, mac_len=4)
    try:
      payload = cipher.decrypt_and_verify(ciphertext[1:-8], mic)
    except ValueError:
      lg.warning('%s', f'Error decrypting payload "{ciphertext!r}" for device "{self.mac}".')
      return False
    #: endtry
    self.ciphertext = ciphertext
    self.counter = new_counter
    self.payload = payload
    lg.debug('%s',  f'Decrypted ciphertext "{ciphertext!r}" for device "{self.mac}" gives '\
                    f'payload "{self.payload!r}".')
    return True
  #: enddef decrypt ////////////////////////////////////////////////////////////


  # ****************************************************************************
  def parse(self) -> dict[str, tuple[bool | str | float, None | str | int]] | None:
    '''Parses a BTHome v2 payload. Returns a dict with measurements, indexed by
        their property name and containing a 2 element tuple with any of:
          1.  (bool, None):   [True/False] for binary sensors
          2.  (value, None):  [str] for 'firmware version', 'text' and 'raw'
                              properties
          3.  (type, None):   [str] for event sensors without event property
          4.  (type, value):  [str, int] for event sensors with event property
          5.  (value, unit):  [float, str] for remaining sensors,
                              unit may be None
        May return None in case there is no valid data.'''
    value: bool | str | float = ''
    measurements: dict[str, tuple[bool | str | float, None | str | int]] = {}
    event_type: str | None = None
    event_property: int | None = None
    payload = self.payload
    # to manage same kind of measurements from same sensor
    measurement_counter = bytearray(b'\00' * 256)
    # walk the payload
    while len(payload) > 1:
      sensor_id = payload[0]
      sensor = SENSOR.get(sensor_id)
      if sensor is None:
        break   # unknown sensor, can't do anymore
      #: endif
      payload = payload[1:]
      property_name = sensor.property
      n_bytes = sensor.bytes
      if sensor.events:
        # is an event sensor
        event_type = sensor.events.get(payload[0])
        event_property = int(payload[1]) if n_bytes == 2 else None
      elif n_bytes:
        # has a fixed size value length
        value_i = int.from_bytes(payload[:n_bytes], byteorder='little', signed=sensor.signed)
        value = float(value_i * sensor.factor)
        # manage packet id
        if sensor_id == 0:
          new_timestamp = time()
          packet_id = self.packet_id
          # only accept payloads that are more than 4 seconds from prior ones
          # or with an increasing packet_id, or with same packet_id and not
          # deduplicating
          if not ((new_timestamp > self.timestamp + 4.0)
              or (value_i > packet_id and value_i - packet_id < 64)
              or (value_i < packet_id and value_i + 256 - packet_id < 64)
              or (value_i == packet_id and not self.deduplicate)):
            lg.debug('%s', f'Packet rejected for device {self.mac} (timestamp or packet_id).')
            measurements = {}   # reject measurements
            break
          #: endif
          self.timestamp = new_timestamp
          self.packet_id = value_i
        #: endif
        if sensor.binary:
          # is a binary sensor
          value = bool(value_i)
        elif 0xF1 <= sensor_id <= 0xF2:
          # is firmware version
          value = f'{value_i:0{2 * n_bytes}x}'
        #: endif
      else:
        # has a variable value length (text 0x53, raw 0x54)
        n_bytes, payload = payload[0], payload[1:]
        value_b: bytes = payload[:n_bytes]
        value = value_b.decode() if sensor_id == 0x53 else value_b.hex()
      #: endif
      payload = payload[n_bytes:]   # skip to next sensor
      # increase the measurements counter for each sensor
      measurement_counter[sensor_id] = cnt = measurement_counter[sensor_id] + 1
      # manage sensor names in case of > 1 measurements from same sensor
      if cnt > 1:
        property_name += '_' + str(cnt)
      #: endif
      if event_type is not None:
        measurements[property_name] = (event_type, event_property)
      elif (not sensor.events) and (sensor_id != 0):  # do not report packet id
        measurements[property_name] = (value, sensor.unit)
      #: endif
    #: endwhile (data available)
    return measurements if measurements else None
  #: enddef parse //////////////////////////////////////////////////////////////


  # ****************************************************************************
  async def publish(self, measurements: dict[str, tuple[bool | str | float, None | str | int]]):
    '''Publishes measurements to MQTT brokers of a BTHome v2 device'''

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    async def connect_to_broker(broker: Broker):
      '''Connects to a broker and spawns publishments on all of its topics'''
      lg.debug('%s', f'({self.mac} => {broker.hostname}) Connecting to MQTT broker.')
      try:
        ssl_context = None
        if broker.encrypt:
          ssl_context = ssl.create_default_context(cafile=_CAFILE, purpose=ssl.Purpose.SERVER_AUTH)
        else:
          broker.insecure = False
        #: endif
        lg.debug('%s',  f'({self.mac} => {broker.hostname}) Connecting '\
                        f'({"with" if broker.encrypt else "without"} encryption, '\
                        f'{"insecure, " if broker.encrypt and broker.insecure else ""}'\
                        f'{"with" if broker.user != "" else "without"} authentication) '\
                        f'to MQTT broker "{broker.hostname}:{broker.port}".')
        async with aiomqtt.Client(
            hostname = broker.hostname,
            username = broker.user,
            password = broker.password,
            port = broker.port,
            tls_context = ssl_context,
            tls_insecure = broker.insecure,
            timeout = _AIOMQTT_TIMEOUT
        ) as peer:
          async with asyncio.TaskGroup() as tg_topic:
            for topic in broker.topics:
              tg_topic.create_task(publish_to_broker(peer, topic))
            #: endfor topic
          #: endwith tg_topic
        #: endwith peer
      except (aiomqtt.MqttError, aiomqtt.MqttCodeError) as e:
        lg.error('%s', f'({self.mac} => {broker.hostname}) MQTT connect error. {e}.')
        return
      #: endtry
      lg.debug('%s', f'({self.mac} => {broker.hostname}) Done with MQTT broker.')
    #: enddef connect_to_broker ------------------------------------------------

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    async def publish_to_broker(peer: aiomqtt.client.Client, topic: str):
      '''MQTT publish to topic of an already connected broker.'''
      full_topic = topic + '/' + self.mac if self.promiscuous else topic
      # remode duplicated '/', just in case...
      full_topic = re.sub(_SLASHES_RE, '/', full_topic)
      lg.debug('%s',  f'({self.mac} => {broker.hostname}) MQTT publishment with payload '\
                      f'\'{mqtt_payload}\' to topic "{full_topic}".')
      try:
        await peer.publish(topic=full_topic, payload=mqtt_payload, timeout=_AIOMQTT_TIMEOUT)
      except (aiomqtt.MqttError, aiomqtt.MqttCodeError) as e:
        lg.error('%s', f'({self.mac} => {broker.hostname}) MQTT publish error. {e}.')
        return
      #: endtry
      lg.debug('%s',  f'({self.mac} => {broker.hostname}) Successful MQTT publishment of payload '\
                      f'\'{mqtt_payload}\' to topic "{full_topic}".')
    #: enddef publish_to_broker ------------------------------------------------

    if not measurements:
      lg.warning('%s', f'({self.mac} => broker) No measurements to publish.')
      return
    #: endif
    mqtt_payload = json.dumps(measurements)
    async with asyncio.TaskGroup() as tg_broker:
      for broker in self.brokers:
        tg_broker.create_task(connect_to_broker(broker))
      #: endfor broker
    #: endwith tg_broker
  #: enddef publish ////////////////////////////////////////////////////////////


#: endclass BTHomeDevice  ######################################################



# Read YAML configuration file  ################################################
def get_bthome_devices_from_yaml_file(config_file_name: str) -> dict[str, BTHomeDevice] | None:
  '''Gets a dict of BTHome v2 devices to listen to (indexed by their MAC address)
      from a YAML file. See the example YAML file for a description.'''
  try:
    lg.info('%s', f'Reading "{config_file_name}" YAML configuration file.')
    with open(config_file_name, 'rt', encoding='utf-8-sig') as config_file:
      try:
        devices_from_yaml = yaml.safe_load(config_file)
        assert isinstance(devices_from_yaml, dict)
      except (yaml.YAMLError, AssertionError) as e:
        lg.critical('%s', f'Cannot parse "{config_file_name}" YAML configuration file '\
                          f'(bad syntax?). {e}. Exiting.')
        return None
      #: endtry
      devices = {}  # devices to monitor, indexed by MAC address
      for mac, device_data in devices_from_yaml.items():
        # remove :-_. and spaces from MAC address
        mac = mac.translate({ord(c): None for c in ':-_. '}).upper()
        bthomedevice = BTHomeDevice(mac=mac)
        key = bytes.fromhex(device_data.get('key', ''))
        if len(key) != 16 and key != b'':
          lg.error('%s', f'Decrypting key for device "{mac}" not 128 bits in length.')
          key = b''
        #: endif
        bthomedevice.key = key
        bthomedevice.deduplicate = device_data.get('deduplicate', bthomedevice.deduplicate)
        for broker_data in device_data.get('brokers'):
          broker = Broker()
          broker.hostname = broker_data.get('hostname', broker.hostname)
          broker.port = broker_data.get('port', broker.port)
          broker.user = broker_data.get('user', broker.user)
          broker.password = broker_data.get('password', broker.password)
          broker.encrypt = broker_data.get('encrypt', broker.encrypt)
          broker.insecure = broker_data.get('insecure', broker.insecure)
          for topic in broker_data.get('topics'):
            # topics cannot be empty
            if topic:
              broker.topics.append(str(topic))
            else:
              lg.warning('%s',  f'Invalid empty topic for broker "{broker.hostname}" '\
                                f'for device "{mac}".')
            #: endif
          #: endfor topic
          # do not add a broker without valid topics
          if broker.topics:
            bthomedevice.brokers.append(broker)
          else:
            lg.warning('%s',  f'Broker "{broker.hostname}" for device "{mac}" not added, '\
                              f'as does not have any valid topic.')
          #: endif
        #: endfor broker
        # do not add a device without valid brokers
        if bthomedevice.brokers:
          devices[mac] = bthomedevice
        else:
          lg.warning('%s', f'Device "{mac}" not added, as does not have any valid broker.')
        #: endif
      #: endfor device
    #: endwith config_file
  except (FileNotFoundError, PermissionError, OSError) as e:
    lg.critical('%s', f'Cannot read "{config_file_name}" configuration file. {e}. Exiting.')
    return None
  #: endtry
  lg.info('%s', f'Configuration file "{config_file_name}" successfully parsed.')
  if not devices:
    lg.critical('%s', 'No valid BTHome devices to listen to, exiting.')
    return None
  #endif
  return devices
#: enddef get_bthome_devices_from_yaml_file ####################################



# ##############################################################################
def create_bthome_decoder(bthome_devices: dict[str, BTHomeDevice], meas_log_lvl: int):
  '''Factory for decoder callbacks for the BLE scanner. Such callbacks decrypt,
      parse and publish BTHome measurements.'''
  _devices = deepcopy(bthome_devices)
  _meas_log_lvl = meas_log_lvl


  # processor for each received BLE advertisement ******************************
  async def decoder(ble_device, advertisement_data):
    '''Decoder callback for the BLE scanner. Decrypts, parses and publishes.'''
    if not advertisement_data.service_data:
      return      # skip no-UUID advertisements
    #: endif
    lg.debug('%s', f'Detected advertising BLE device {ble_device}.')
    mac = ble_device.address.replace(':', '').upper()
    bthome_device = _devices.get(mac)
    if (bthome_device is None) and ('PROMISCUOUS' not in _devices.keys()):
      lg.debug('%s', f'Skipping unwanted BLE device {ble_device}.')
      return      # skip new devices in non-promiscuous mode
    #: endif
    # walk UUIDs
    for uuid, data in advertisement_data.service_data.items():
      if uuid[4:8].lower() != _BTHOME_UUID:
        continue  # skip non BTHome UUIDs
      #: endif
      device_info = data[0]
      if device_info >> 5 != 0b010:
        continue  # skip non v2 BTHome protocols
      #: endif
      if bthome_device is None:
        # create new device in promiscuous mode
        bthome_device = deepcopy(_devices['PROMISCUOUS'])
        bthome_device.mac = mac
        bthome_device.promiscuous = True
        _devices[mac] = bthome_device
        lg.debug('%s', f'Added new BLE device {ble_device} in promiscuous mode.')
      #: endif
      # check for encryption
      if not bool(device_info & 0b1):
        # not encrypted
        if bthome_device.deduplicate and bthome_device.payload == data[1:]:
          continue  # skip repeated payloads (if instructed to do so)
        #: endif
        bthome_device.payload = data[1:]
      elif not bthome_device.decrypt(data): # decrypt if encrypted
        continue    # skip if decryption fails
      #: endif
      measurements = bthome_device.parse()
      if measurements:
        measurements['RSSI'] = (float(advertisement_data.rssi), 'dBm')
        lg.log(_meas_log_lvl, '%s', f'Data from device {ble_device}: {measurements}.')
        await bthome_device.publish(measurements)
      else:
        lg.warning('%s', f'BLE device {ble_device} does not report any valid BTHome v2 data.')
      #: endif
    #: endfor uuid
  #: enddef decoder ////////////////////////////////////////////////////////////


  return decoder    # return the decoder as a closure
#: enddef create_bthome_decoder ################################################
