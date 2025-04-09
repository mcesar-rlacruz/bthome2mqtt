#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''Launches a BLE scan for BTHome v2 devices, publishing received measurements
    thru MQTT'''



# ##############################################################################
import argparse
import numbers
import os
import sys
from   logging.handlers import RotatingFileHandler
import logging as lg
import asyncio
import signal
import platform
import functools
# ..............................................................................
import bleak
# ..............................................................................
from   bthome_decoder import get_bthome_devices_from_yaml_file, create_bthome_decoder
# ##############################################################################



# ##############################################################################
async def main():
  '''Simply... main()'''


  # process command line arguments  ********************************************
  arg_parser = argparse.ArgumentParser(
      description = 'Monitor BTHome v2 devices and publish to MQTT brokers.')
  arg_parser.add_argument('-c', '--config-file', action = 'store',
    default = 'bthome_devices.yaml',
    help =  'file describing the BTHome devices to monitor and where to send (MQTT) '\
            'their measurements. Defaults to "bthome_devices.yaml".',
    dest = 'config_file_name')
  arg_parser.add_argument('-a', '--adapter', action = 'store',
    default = None,
    help =  'Bluetooth HCI adapter to use (hci0, hci1, ...). Used only in Linux/BlueZ. '\
            'If not specified, uses system default.',
    dest = 'adapter')
  arg_parser.add_argument('-s', '--scan_time', action = 'store',
    default = 0, type = float,
    help =  'BLE scan time (in s). Defaults to 0. A <= 0 number is treated as '\
            '"scan with no pauses".',
   dest = 'scan_time')
  arg_parser.add_argument('-p', '--scan-pause', action = 'store',
    default = 1, type = float,
    help = 'pause time between scans (in s). Defaults to 1. Ignored if SCAN_TIME <= 0.',
    dest = 'scan_pause')
  arg_parser.add_argument('-l', '--log-file', action = 'store',
    default = None,
    help = 'file where to write log messages. If not set, outputs messages to standard error.',
    dest = 'log_file_name')
  arg_parser.add_argument('-m', '--measurements_as_info', action = 'store_true',
    help = 'log measurements as INFO, instead of as DEBUG.',
    dest = 'log_measurements_as_info')
  arg_parser.add_argument('--log-level', action = 'store',
    default = 'INFO',
    choices = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
    help = 'set log level. Defaults to "INFO".',
    dest = 'log_level')
  arg_parser.add_argument('-t', '--timestamp', action = 'store_true',
    help = 'include timestamps into log messages.',
    dest = 'log_timestamp')
  arg_parser.add_argument('-d', '--date', action = 'store_true',
    help = 'include date into timestamps.',
    dest = 'log_date')

  args = arg_parser.parse_args()
  config_file_name = args.config_file_name
  adapter = args.adapter
  scan_time = args.scan_time
  scan_pause = args.scan_pause
  log_file_name = args.log_file_name
  log_level = getattr(lg, args.log_level)
  log_measurements_as_info = args.log_measurements_as_info
  log_date = args.log_date
  log_timestamp = args.log_timestamp
  # ////////////////////////////////////////////////////////////////////////////


  # configure logging **********************************************************
  lg.basicConfig(
      handlers = [lg.StreamHandler()] if log_file_name is None
          else [RotatingFileHandler(log_file_name, maxBytes=1000000, backupCount=5)],
      encoding = 'utf-8',
      style = '%',
      format = ('%(asctime)s.%(msecs)03d - ' if log_timestamp else '')
          + '%(levelname)s: %(message)s',
      datefmt = '%Y-%m-%dT%H:%M:%S' if log_date else '%H:%M:%S',
      level = log_level)
  meas_log_lvl = lg.INFO if log_measurements_as_info else lg.DEBUG
  lg.info('%s', f'{__file__} started.')
  lg.info('%s', f'Log level = {args.log_level}')
  # ////////////////////////////////////////////////////////////////////////////


  # check input arguments ******************************************************
  if not isinstance(scan_time, numbers.Number):
    lg.critical('%s', f'Invalid value {scan_time} for command line argument "scan_time". Exiting.')
    return
  #: endif
  if not isinstance(scan_pause, numbers.Number) or scan_pause <= 0:
    lg.critical('%s', f'Invalid value {scan_pause} for command line argument '\
                      f'"scan_pause". Exiting.')
    return
  #: endif
  if scan_time <= 0:
    scan_time = sys.float_info.max
    scan_pause = 0.1
  #: endif  ////////////////////////////////////////////////////////////////////


  # Read config file  **********************************************************
  bthome_devices = get_bthome_devices_from_yaml_file(config_file_name)
  if bthome_devices is None:
    return
  #: endif  ////////////////////////////////////////////////////////////////////


  # manage program termination  ************************************************
  stop_event = asyncio.Event()
  loop = asyncio.get_event_loop()

  # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
  def signal_handler(signal_name_or_number, loop_or_frame):
    global reload
    if platform_system == 'Windows':
      lg.warning('%s', f'Caught signal {signal.Signals(signal_name_or_number).name}, terminating.')
    else:
      lg.warning('%s', f'Caught signal {signal_name_or_number}, terminating.')
      # to reload when running as a daemon
      if signal_name_or_number == 'SIGHUP':
        reload = True
        lg.info('%s', 'Will reload due to signal HUP.')
      #: endif
    #: endif
    stop_event.set()
  #: enddef signal_handler  ----------------------------------------------------

  terminating_signal_names = ['SIGINT', 'SIGTERM', 'SIGABRT']
  if platform_system in ('Linux', 'Darwin'):  # Darwin not tested !!!
    terminating_signal_names += ('SIGHUP', 'SIGQUIT')
  elif platform_system == 'Windows':
    terminating_signal_names += ('SIGBREAK', )
  #: endif
  for signal_name in terminating_signal_names:
    if platform_system == 'Windows':
      signal.signal(getattr(signal, signal_name), signal_handler)
    else:
      loop.add_signal_handler(
          getattr(signal, signal_name),
          functools.partial(signal_handler, signal_name, loop))
    #: endif
  # :enfor  ////////////////////////////////////////////////////////////////////


  # ****************************************************************************
  # get parameters for bleak.BleakScanner
  bluez_args = []
  match platform_system:
    case 'Windows':
      scanning_mode = 'passive'
      adapter = None
    case 'Linux':
      from bleak.backends.bluezdbus.scanner import BlueZScannerArgs
      from bleak.backends.bluezdbus.advertisement_monitor import OrPattern
      from bleak.assigned_numbers import AdvertisementDataType
      scanning_mode = 'passive'
      bluez_args = BlueZScannerArgs(
          or_patterns = [OrPattern(0, AdvertisementDataType.SERVICE_DATA_UUID16, b"\xd2\xfc")])
    case 'Darwin':  # not tested !!!
      scanning_mode = 'active'
      adapter = None
    case _:
      lg.critical('%s', f'System "{platform_system}" not supported. Exiting.')
      return
  #: endmatch
  lg.info('%s', f'Platform "{platform_system}" detected.')
  lg.debug('%s',  f'BLE scanner parameters: scanning_mode = {scanning_mode}, '\
                  f'bluez = {repr(bluez_args)}.')
  # ////////////////////////////////////////////////////////////////////////////


  # scan  **********************************************************************
  lg.info('%s', 'Starting BLE scanner.')
  try:
    bthome_decoder = create_bthome_decoder(bthome_devices, meas_log_lvl)
    async with bleak.BleakScanner(
        bthome_decoder,
        scanning_mode = scanning_mode,
        bluez = bluez_args,
        adapter = adapter) as scanner:
      lg.info('%s', f'BLE scanner started ({scan_time} s on / {scan_pause} s off).')
      while True:
        try:
          await asyncio.wait_for(stop_event.wait(), scan_time)
        except TimeoutError:
          await scanner.stop()
          lg.debug('BLE scanner stopped.')
        else:
          break
        #: endtry
        try:
          await asyncio.wait_for(stop_event.wait(), scan_pause)
        except TimeoutError:
          lg.debug('BLE scanner restarted.')
          await scanner.start()
        else:
          break
        #: endtry
      #: endwhile
    #: endwith scanner
  except OSError as e:
    lg.critical('%s', f'OS error "{e}" (BLE adapter not ready/enabled?), terminating.')
  except Exception as e:
    lg.critical('%s', f'Unmanaged exception "{e}", terminating.')
  else: # normal termination
    lg.info('BLE scanner stopped.')
  finally:
    lg.info('Exiting.')
  #: endtry ////////////////////////////////////////////////////////////////////


#: endef main ##################################################################



# ##############################################################################
if __name__ == '__main__':
  reload = False
  platform_system = platform.system()
  if platform_system == "Windows":
    # required by aiomqtt
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
  #: endif
  asyncio.run(main())
  # reload daemon (if signal HUP arrived)
  if reload:
    os.execv(sys.executable, [sys.executable] + sys.argv)
  #: endif
#: endif  ######################################################################
