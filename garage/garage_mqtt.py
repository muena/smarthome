import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import time
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv("/home/pi/.garage_mqtt.env")
BROKER = os.getenv("MQTT_BROKER")
PORT = int(os.getenv("MQTT_PORT", 1883))
USERNAME = os.getenv("MQTT_USERNAME")
PASSWORD = os.getenv("MQTT_PASSWORD")
CLIENT_ID = "garage_pi"

# GPIO pins
TOR_MITTE_RELAIS = 16
TOR_RECHTS_RELAIS = 26
TOR_MITTE_OFFEN = 27
TOR_MITTE_GESCHLOSSEN = 22
TOR_RECHTS_OFFEN = 24
TOR_RECHTS_GESCHLOSSEN = 23

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup([TOR_MITTE_RELAIS, TOR_RECHTS_RELAIS], GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup([TOR_MITTE_OFFEN, TOR_MITTE_GESCHLOSSEN, TOR_RECHTS_OFFEN, TOR_RECHTS_GESCHLOSSEN],
           GPIO.IN, pull_up_down=GPIO.PUD_UP)

client = mqtt.Client(client_id=CLIENT_ID)
client.username_pw_set(USERNAME, PASSWORD)
client.enable_logger()

last_state_mitte = None
last_state_rechts = None

# Determine current state
def calc_state(offen_pin, geschlossen_pin, last_state):
    if GPIO.input(offen_pin) == 0:
        return "open"
    elif GPIO.input(geschlossen_pin) == 0:
        return "closed"
    else:
        if last_state == "open":
            return "closing"
        elif last_state == "closed":
            return "opening"
        else:
            return "unknown"

def publish_state():
    global last_state_mitte, last_state_rechts

    mitte = calc_state(TOR_MITTE_OFFEN, TOR_MITTE_GESCHLOSSEN, last_state_mitte)
    rechts = calc_state(TOR_RECHTS_OFFEN, TOR_RECHTS_GESCHLOSSEN, last_state_rechts)

    if mitte in ["open", "closed"]:
        last_state_mitte = mitte
    if rechts in ["open", "closed"]:
        last_state_rechts = rechts

    client.publish("garage/tor_mitte/state", mitte, retain=True)
    client.publish("garage/tor_rechts/state", rechts, retain=True)

def publish_discovery():
    discovery_mitte = {
        "name": "Tor Mitte",
        "command_topic": "garage/tor_mitte/set",
        "state_topic": "garage/tor_mitte/state",
        "payload_open": "open",
        "payload_close": "close",
        "state_open": "open",
        "state_closed": "closed",
        "state_opening": "opening",
        "state_closing": "closing",
        "device_class": "garage",
        "retain": True,
        "unique_id": "garage_tor_mitte"
    }

    discovery_rechts = {
        "name": "Tor Rechts",
        "command_topic": "garage/tor_rechts/set",
        "state_topic": "garage/tor_rechts/state",
        "payload_open": "open",
        "payload_close": "close",
        "state_open": "open",
        "state_closed": "closed",
        "state_opening": "opening",
        "state_closing": "closing",
        "device_class": "garage",
        "retain": True,
        "unique_id": "garage_tor_rechts"
    }

    client.publish("homeassistant/cover/tor_mitte/config", json.dumps(discovery_mitte), retain=True)
    client.publish("homeassistant/cover/tor_rechts/config", json.dumps(discovery_rechts), retain=True)
    print("Home Assistant discovery configuration published")

def on_message(client, userdata, msg):
    global last_state_mitte, last_state_rechts

    command = msg.payload.decode().lower()
    print(f"Command received: {msg.topic} -> {command}")

    if msg.topic == "garage/tor_mitte/set":
        current_state = calc_state(TOR_MITTE_OFFEN, TOR_MITTE_GESCHLOSSEN, last_state_mitte)

        if command == "open" and current_state != "open":
            print("Opening Tor Mitte")
            GPIO.output(TOR_MITTE_RELAIS, GPIO.LOW)
            time.sleep(0.5)
            GPIO.output(TOR_MITTE_RELAIS, GPIO.HIGH)
            client.publish("garage/tor_mitte/state", "opening", retain=True)

        elif command == "close" and current_state != "closed":
            print("Closing Tor Mitte")
            GPIO.output(TOR_MITTE_RELAIS, GPIO.LOW)
            time.sleep(0.5)
            GPIO.output(TOR_MITTE_RELAIS, GPIO.HIGH)
            client.publish("garage/tor_mitte/state", "closing", retain=True)

        elif command == "stop":
            print("Stopping Tor Mitte")
            GPIO.output(TOR_MITTE_RELAIS, GPIO.LOW)
            time.sleep(0.5)
            GPIO.output(TOR_MITTE_RELAIS, GPIO.HIGH)

        else:
            print("Command ignored (no change)")

    elif msg.topic == "garage/tor_rechts/set":
        current_state = calc_state(TOR_RECHTS_OFFEN, TOR_RECHTS_GESCHLOSSEN, last_state_rechts)

        if command == "open" and current_state != "open":
            print("Opening Tor Rechts")
            GPIO.output(TOR_RECHTS_RELAIS, GPIO.LOW)
            time.sleep(0.5)
            GPIO.output(TOR_RECHTS_RELAIS, GPIO.HIGH)
            client.publish("garage/tor_rechts/state", "opening", retain=True)

        elif command == "close" and current_state != "closed":
            print("Closing Tor Rechts")
            GPIO.output(TOR_RECHTS_RELAIS, GPIO.LOW)
            time.sleep(0.5)
            GPIO.output(TOR_RECHTS_RELAIS, GPIO.HIGH)
            client.publish("garage/tor_rechts/state", "closing", retain=True)

        elif command == "stop":
            print("Stopping Tor Rechts")
            GPIO.output(TOR_RECHTS_RELAIS, GPIO.LOW)
            time.sleep(0.5)
            GPIO.output(TOR_RECHTS_RELAIS, GPIO.HIGH)

        else:
            print("Command ignored (no change)")

    publish_state()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        client.subscribe("garage/+/set")
        publish_discovery()
        publish_state()
    else:
        print(f"Connection failed (Code {rc})")

client.on_connect = on_connect
client.on_message = on_message

print(f"Connecting to MQTT broker {BROKER}:{PORT} ...")
client.connect(BROKER, PORT, 60)
client.loop_start()

try:
    while True:
        publish_state()
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopping script...")
finally:
    GPIO.cleanup()
    client.loop_stop()