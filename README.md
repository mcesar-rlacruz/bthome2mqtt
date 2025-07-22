# bthome2mqtt, a MQTT publisher for BTHome v2 advertisements

This repo contains a Python program able to (passively) listen to BTHome v2 devices and, then, publish the received measurements to MQTT brokers.

The program supports both encrypted and un-encrypted BTHome v2 advertisements and reports the measurements to one or more MQTT brokers, supporting both authentication and encryption when sending data to these brokers.

The program is _daemonizable_ to be run as a service under a `systemd` based Linux system. An example `.service` file is provided.

The configuration of the program (sensors to listen to, decryption keys, brokers where to publish measurements, encryption, authentication, topics, etc.) are specified in a configuration file in the YAML human-readable data serialization language. Read the comments on the provided example file to learn how to write it.

The program is formed by three scripts written in Python (v3) using asynchronous IO (`async`/`await`) to manage all BLE/MQTT communications. Packages `asyncio`, `bleak` and `aiomqtt` are used for that. These asynchronous IO approach gives low CPU and memory usage even when managing many sensors and brokers.

## Requirements

### Hardware

You will need:

* One or more BTHome v2 devices to listen to. For each device you need to know its MAC address and, if encrypted, its 128 bit (32 hex digit) decryption key. There is also provision for a 'promiscuous' mode where the MAC address is not needed, see the example YAML configuration file (note that, in this case, all BTHome v2 devices with an unknown MAC address must be unencrypted, or encrypted with the same decryption key).
* A Bluetooth LE capable Windows® (≥ 10) or Linux box (supporting `BlueZ` ≥ 5.43). Sorry, not tested on MacOS. A Raspberry Pi is enough (with its built-in Bluetooth or with an OS-supported BLE dongle).

### Software

You will need:

* Python (≥ 3.8)
* Python packages: `yaml`, `types-PyYAML`, `bleak`, `cryptodome` and `aiomqtt`.

Depending on the OS and its version, you may need to install them with the usual `pip` (add the `sudo` only in Linux and if you want all packages to be installed system-wide):

```shell
sudo pip install pyyaml types-pyyaml bleak pycryptodomex aiomqtt
```

or (in Debian Bookworm):

```shell
sudo apt install python3-yaml python3-types-pyyaml python3-bleak python3-pycryptodome
```

On Bookworm, `aiomqtt` must be installed with:

```shell
sudo apt install python3-pip
sudo pip install aiomqtt --break-system-packages
```

so, maybe, you may prefer to install `aiomqtt` inside a Python virtual environment.

Then, on Linux, file `/usr/lib/systemd/system/bluetooth.service` must be edited:

```shell
sudo nano /usr/lib/systemd/system/bluetooth.service
```

in order to add option `--experimental` to line:

```shell
ExecStart=/usr/libexec/bluetooth/bluetoothd --experimental
```

then:

```shell
sudo systemctl daemon-reload
sudo systemctl restart bluetooth
```

That's all, copy the three supplied `.py` file where you want and then `bthome2mqtt.py` can now be tested from the command line:

```shell
pi@rpiz2w:~ $ ./bthome2mqtt.py -h
usage: bthome2mqtt.py [-h] [-c CONFIG_FILE_NAME] [-a ADAPTER] [-s SCAN_TIME] [-p SCAN_PAUSE] [-l LOG_FILE_NAME] [-m] [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [-t] [-d]

Monitor BTHome v2 devices and publish to MQTT brokers.

options:
  -h, --help            show this help message and exit
  -c CONFIG_FILE_NAME, --config-file CONFIG_FILE_NAME
                        file describing the BTHome devices to monitor and where to send (MQTT) their measurements. Defaults to "bthome_devices.yaml".
  -a ADAPTER, --adapter ADAPTER
                        Bluetooth HCI adapter to use (hci0, hci1, ...). Used only in Linux/BlueZ. If not specified, uses system default.
  -s SCAN_TIME, --scan_time SCAN_TIME
                        BLE scan time (in s). Defaults to 0. A <= 0 number is treated as "scan with no pauses".
  -p SCAN_PAUSE, --scan-pause SCAN_PAUSE
                        pause time between scans (in s). Defaults to 1. Ignored if SCAN_TIME <= 0.
  -l LOG_FILE_NAME, --log-file LOG_FILE_NAME
                        file where to write log messages. If not set, outputs messages to standard error.
  -m, --measurements_as_info
                        log measurements as INFO, instead of as DEBUG.
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        set log level. Defaults to "INFO".
  -t, --timestamp       include timestamps into log messages.
  -d, --date            include date into timestamps.
```


## Usage

When invoked from the command line, `bthome2mqtt.py` supports options:

```shell
usage: bthome2mqtt.py [-h] [-c CONFIG_FILE_NAME] [-a ADAPTER] [-s SCAN_TIME] [-p SCAN_PAUSE] [-l LOG_FILE_NAME] [-m] [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [-t] [-d]

options:
  -h, --help            show this help message and exit
  -c CONFIG_FILE_NAME, --config-file CONFIG_FILE_NAME
                        file describing the BTHome devices to monitor and where to send (MQTT) their measurements. Defaults to "bthome_devices.yaml".
  -a ADAPTER, --adapter ADAPTER
                        Bluetooth HCI adapter to use (hci0, hci1, ...). Used only in Linux/BlueZ. If not specified, uses system default.
  -s SCAN_TIME, --scan_time SCAN_TIME
                        BLE scan time (in s). Defaults to 0. A <= 0 number is treated as "scan with no pauses".
  -p SCAN_PAUSE, --scan-pause SCAN_PAUSE
                        pause time between scans (in s). Defaults to 1. Ignored if SCAN_TIME <= 0.
  -l LOG_FILE_NAME, --log-file LOG_FILE_NAME
                        file where to write log messages. If not set, outputs messages to standard error.
  -m, --measurements_as_info
                        log measurements as INFO, instead of as DEBUG.
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        set log level. Defaults to "INFO".
  -t, --timestamp       include timestamps into log messages.
  -d, --date            include date into timestamps.
```

All these options seem self-explanatory. Only `-s` and `-p` may require a comment. When passively scanning for BLE advertisements, some backends (Linux with some chipsets) report each BLE device only once. Thus, in order to continuously report advertisements from the same devices, it is necessary to scan for a while and then stop the scanning in order to relaunch it later. Options `-s` and `-p` set the duration (in s) of these scan and pause between scans periods, respectively. If option `-s 0` is given, scanning never pauses. If your sensors have and advertisement period of, say, T seconds, a small multiple of T may be enough for `-s`. Test your system for expected behavior before setting option `-s 0`.

By default, the log does not contain timestamps. This is because, when run as a daemon/service, the log messages are managed by `journald`, that inserts them. Inserting timestamps in the log may be controlled with options `-t` and `-d`.

## Configuration

The configuration describing the BTHome v2 devices to listen to and the brokers where to publish the measurements is contained in a configuration file (whose name may be specified from the command line) in the YAML language. Please, read the provided `bthome_devices.yaml` example configuration file to learn how to write its contents.

## Run as a service

In Linux this script can be run as a daemon. This is achieved creating a service that `systemd` will start at boot. To accomplish this task an example `bthome2mqtt.service` file is provided. Its contents are:

```shell
[Unit]
Description=Monitor BTHome v2 advertisments and publish to MQTT brokers
Wants=multi-user.target bluetooth.service
After=bluetooth.service

[Service]
ExecStart=/usr/bin/python3 /home/pi/bthome2mqtt.py -s600 -p0.1 -c /home/pi/bthome_devices.yaml
ExecReload=/usr/bin/kill -HUP $MAINPID
User=pi

[Install]
WantedBy=default.target
```

You may want to edit line `ExecStart=/usr/bin/python3 /home/pi/bthome2mqtt.py -s600 -p0.1 -c /home/pi/bthome_devices.yaml` to better fit your needs. This file must be placed inside `/usr/lib/systemd/system`, owned by `root:root` with permission `640`, this is:

```shell
sudo cp bthome2mqtt.service /usr/lib/systemd/system
sudo chown root:root /usr/lib/systemd/system/bthome2mqtt.service
sudo chmod 640 /usr/lib/systemd/system/bthome2mqtt.service
```

Then the service can be enabled and started:

```shell
sudo systemctl daemon-reload
sudo systemctl enable --now bthome2mqtt
```

From now on, `bthome2mqtt` will be running in the system, automatically launched at boot. It can be stopped/started/restarted/reloaded (to re-read its YAML configuration file) with `sudo systemctl stop/start/restart/reload bthome2mqtt`. Its status can be viewed with `sudo systemctl status bthome2mqtt`.

When run as a service, its log is managed by the `journald` service, and can be read with `journalctl -u bthome2mqtt`.

## MQTT payload format

Each advertisement from a BTHome v2 device is sent to MQTT brokers as a single string containing a JSON object literal, for example: from an hypothetical BTHome v2 device capable of measuring UV index, provided with some buttons, some dimmers and a window sensor, string `'{"battery": [80.0, "%"], "UV index": [6.8, null], "text": ["Hello, World!", null], "button_3": ["press", null], "dimmer_2": ["rotate_right", 5], "window": [true, null], "RSSI": [-73.0, "dBm"]}'`, represents JSON object:

```json
{
    "battery": [80.0, "%"],
    "UV index": [6.8, null],
    "text": ["Hello, World!", null],
    "button_3": ["press", null],
    "dimmer_2": ["rotate_right", 5],
    "window": [true, null],
    "RSSI": [-73.0, "dBm"]
}
```

The `name` of each `name:value` pair corresponds to a `property` (or `device type` for event devices —only `button` and `dimmer` currently—) as described in the [BTHome v2 format]([Reference – BTHome](https://bthome.io/format/)) specification. Each `value` is a two element array there are five variants of:

1. `[float_number, string]`: these are the measured value and the measurement unit (`battery` and `RSSI` in the example above).
2. `[float_number, null]`: as previous, but there is no measurement unit (`UV index` above).
3. `[string, null]`: for:
   * `firmware version`, `text` (above) and `raw` properties;
   * event sensors _without_ event property (currently only `button`), where the string is the `event type`. Note that `None` event types are not published to MQTT. See `button_3` in the example.
4. `[string, integer_number]`: for event sensors _with_ event property (currently only `dimmer`), where the string is the `event type` and the integer number is the `event property` (`dimmer_2` above).
5. `[boolean, none]`: for binary sensors (`window`, which is open, in the example).

Non-ASCII chars are `\`-escaped in the published strings. For example, a measurement of 18.50 ºC is published as `[18.50, "\\u00b0C"]`.

Property `packet id` is never published to brokers, same happens with events with `event type` equal to `None`. Property `RSSI` is not described in the BTHome v2 specification, but added by this program as a measure of the received BLE signal strength, in units of dBm.

In case that some BTHome v2 device contains multiple instances of the same `property` (say, a device with four buttons), then, from the second instance and up, an underscore and a sequential number are added to the property name. In this example device with four buttons, the properties reported will be: `button`; `button_2`; `button_3`; and `button_4` (note that there is no `button_1`).



