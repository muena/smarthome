# Smart Home

This repository contains my personal collection of smart home scripts and configurations, mainly focused on **Home Assistant** and **Raspberry Pi** devices.
It is a growing toolkit of automations, integrations, and custom services to improve and extend my home automation setup.

---

## Table of Contents

- [Garage MQTT Service](#garage-mqtt-service)

---

## Garage MQTT Service

This service controls two garage doors via a Raspberry Pi, publishes their states via MQTT, and integrates automatically into Home Assistant using **MQTT Discovery**.

### Features

- Automatic detection of the garage doors in Home Assistant (no manual configuration required)
- Accurate state detection: `open`, `closed`, `opening`, `closing`
- Smart command handling: ignores redundant commands (e.g., "open" if the door is already open)
- Supports `open`, `close`, and `stop` commands
- Retained MQTT messages ensure correct state after restarts

---

### Requirements

- Raspberry Pi with Python 3.7 or higher installed
- Installed Python packages:

```bash
pip install paho-mqtt RPi.GPIO python-dotenv
```

- MQTT broker (e.g., Mosquitto) accessible to the Raspberry Pi
- Home Assistant with the MQTT integration enabled

---

### Installation

#### 1. Clone the repository

```bash
git clone https://github.com/muena/smarthome.git
cd smarthome
```

#### 2. Create the `.env` file

Create `/home/pi/.garage_mqtt.env` (or in the same directory as the script, if you adjust the path in the code):

```
MQTT_BROKER=192.168.x.x
MQTT_USERNAME=your_mqtt_user
MQTT_PASSWORD=your_mqtt_password
MQTT_PORT=1883
```

Make sure:
- No quotes around the values
- No spaces around `=`

#### 3. Set file permissions

```bash
chmod 600 /home/pi/.garage_mqtt.env
```

#### 4. Test the script (optional)

Run the script manually to verify it works:

```bash
python3 garage_mqtt.py
```

You should see output similar to:

```
Connecting to MQTT broker 192.168.x.x:1883 ...
Connected to MQTT broker
Publish state: Tor Mitte = closed, Tor Rechts = open
```

---

### Running as a systemd Service

#### 1. Create the service file

Create `/etc/systemd/system/garage_mqtt.service`:

```ini
[Unit]
Description=Garage MQTT Service
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/garage_mqtt.py
WorkingDirectory=/home/pi
EnvironmentFile=/home/pi/.garage_mqtt.env
StandardOutput=journal
StandardError=journal
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

Replace `/usr/bin/python3` with the path from `which python3` if different.

#### 2. Enable and start the service

```bash
sudo systemctl daemon-reexec
sudo systemctl enable garage_mqtt.service
sudo systemctl start garage_mqtt.service
```

#### 3. Check logs

```bash
journalctl -u garage_mqtt.service -f
```

---

### Home Assistant Integration

- The garage doors appear automatically in Home Assistant after the service starts, thanks to **MQTT Discovery**.
- Entities created:
  - `cover.tor_mitte`
  - `cover.tor_rechts`

You can control the garage doors directly from the Lovelace dashboard.
