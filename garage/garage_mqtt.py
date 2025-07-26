import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import time
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/home/pi/.garage_mqtt.env")
BROKER = os.getenv("MQTT_BROKER", "192.168.x.x")
PORT = int(os.getenv("MQTT_PORT", 1883))
USERNAME = os.getenv("MQTT_USERNAME", "homeassistant")
PASSWORD = os.getenv("MQTT_PASSWORD", "geheim")
CLIENT_ID = "garage_pi"

# GPIO pins configuration
TOR_CONFIG = {
    "tor_mitte": {
        "relay": 16,
        "open": 27,
        "closed": 22
    },
    "tor_rechts": {
        "relay": 26,
        "open": 24,
        "closed": 23
    }
}

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup([TOR_CONFIG["tor_mitte"]["relay"], TOR_CONFIG["tor_rechts"]["relay"]],
           GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup([TOR_CONFIG["tor_mitte"]["open"], TOR_CONFIG["tor_mitte"]["closed"],
            TOR_CONFIG["tor_rechts"]["open"], TOR_CONFIG["tor_rechts"]["closed"]],
           GPIO.IN, pull_up_down=GPIO.PUD_UP)

client = mqtt.Client(client_id=CLIENT_ID)
client.username_pw_set(USERNAME, PASSWORD)
client.enable_logger()

last_states = {
    "tor_mitte": None,
    "tor_rechts": None
}

# Determine current state
def calc_state(open_pin, closed_pin, last_state):
    if GPIO.input(open_pin) == 0:
        return "open"
    elif GPIO.input(closed_pin) == 0:
        return "closed"
    else:
        if last_state in ("open", "closing"):
            return "closing"
        elif last_state in ("closed", "opening"):
            return "opening"
        else:
            return "unknown"

def publish_state(force=False):
    for tor, config in TOR_CONFIG.items():
        previous_state = last_states.get(tor)
        state = calc_state(config["open"], config["closed"], previous_state)

        if force or state != previous_state:
            print(f"Publish state: {tor} = {state}")
            client.publish(f"garage/{tor}/state", state, retain=True)
            last_states[tor] = state
            print(f"Tor {tor} ist {state}")

def publish_discovery():
    for tor in TOR_CONFIG.keys():
        discovery_payload = {
            "name": f"{'Tor Mitte' if tor == 'tor_mitte' else 'Tor Rechts'}",
            "command_topic": f"garage/{tor}/set",
            "state_topic": f"garage/{tor}/state",
            "payload_open": "open",
            "payload_close": "close",
            "state_open": "open",
            "state_closed": "closed",
            "state_opening": "opening",
            "state_closing": "closing",
            "device_class": "garage",
            "unique_id": f"garage_{tor}"
        }
        client.publish(f"homeassistant/cover/{tor}/config",
                       json.dumps(discovery_payload), retain=True)
    print("Home Assistant discovery configuration published")

def toggle_relay(relay_pin):
    GPIO.output(relay_pin, GPIO.LOW)
    time.sleep(0.5)
    GPIO.output(relay_pin, GPIO.HIGH)

def on_message(client, userdata, msg):
    if msg.retain:
        print(f"Ignoring retained command: {msg.topic} -> {msg.payload.decode()}")
        return

    command = msg.payload.decode().lower()
    print(f"Command received: {msg.topic} -> {command}")

    for tor, config in TOR_CONFIG.items():
        if msg.topic == f"garage/{tor}/set":
            current_state = calc_state(config["open"], config["closed"], last_states[tor])

            if command == "open" and current_state != "open":
                print(f"Opening {tor}")
                toggle_relay(config["relay"])
                client.publish(f"garage/{tor}/state", "opening", retain=True)

            elif command == "close" and current_state != "closed":
                print(f"Closing {tor}")
                toggle_relay(config["relay"])
                client.publish(f"garage/{tor}/state", "closing", retain=True)

            elif command == "stop" and current_state not in ("open", "closed"):
                print(f"Stopping {tor} (current_state={current_state})")
                toggle_relay(config["relay"])

            else:
                print("Command ignored (no change)")
    publish_state(force=True)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        client.subscribe("garage/+/set")

        for tor, config in TOR_CONFIG.items():
            last_states[tor] = calc_state(config["open"], config["closed"], last_states[tor])

        publish_discovery()
        publish_state(force=True)
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
        time.sleep(5)
except KeyboardInterrupt:
    print("Stopping script...")
finally:
    GPIO.cleanup()
    client.loop_stop()
