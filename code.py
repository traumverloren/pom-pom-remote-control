import supervisor
import os
import microcontroller
import gc
import time
import board
import ssl
import socketpool
import wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_minimqtt.adafruit_minimqtt import MMQTTException

import digitalio
import touchio

# Create a socket pool
pool = socketpool.SocketPool(wifi.radio)

### Code ###
touch_A2 = touchio.TouchIn(board.A2)
touch_A2.threshold = 30000
is_touched = False

def network_connect():
    try:
        print("Connecting to %s" % os.getenv("ssid"))
        wifi.radio.connect(os.getenv("ssid"), os.getenv("wifi_pw"))
        print("Connected to %s!" % os.getenv("ssid"))
        print("My IP address is", wifi.radio.ipv4_address)
    except ConnectionError as e:
        reset_on_error(10, e)


# Define callback methods which are called when events occur
# pylint: disable=unused-argument, redefined-outer-name
def connected(client, userdata, flags, rc):
    # This function will be called when the client is connected
    # successfully to the broker.
    print("Connected to broker!")


def disconnected(client, userdata, rc):
    print("Disconnected from broker!")

def mqtt_connect():
    global client

    # Set up a MiniMQTT Client
    client = MQTT.MQTT(
        broker=os.getenv("broker"),
        port=os.getenv("port"),
        username=os.getenv("user"),
        password=os.getenv("pw"),
        client_id=os.getenv("client_id"),
        socket_pool=pool,
        ssl_context=ssl.create_default_context(),
        keep_alive=60,
    )

    # Setup the callback methods above
    client.on_connect = connected
    client.on_disconnect = disconnected

    # Connect the client to the MQTT broker.
    print("Connecting to MQTT broker...")
    client.connect()


def reset_on_error(delay, error):
    print("Error:\n", str(error))
    print("Resetting microcontroller in %d seconds" % delay)
    time.sleep(delay)
    microcontroller.reset()

def reconnect():
    print("Restarting...")
    network_connect()
    client.reconnect()


last_ping = 0
ping_interval = 30

# start execution
try:
    print("Connecting WIFI")
    network_connect()
    print("Connecting MQTT")
    mqtt_connect()
except KeyboardInterrupt:
    sys.exit()
except Exception:
    raise

while True:
    try:
        # check wifi is connected:
        if wifi.radio.connected == False:
            print("wifi disconnected")
            reconnect()

        #print("mem start loop:", gc.mem_free())
        if (time.time() - last_ping) > ping_interval:
            print("ping broker")
            client.ping()
            last_ping = time.time()

        #print(touch_A2.raw_value)
        if touch_A2.value:
            print(touch_A2.value)
            print("touched!")

            # Send a new message
            print("Answering door...")
            client.publish("doorbell", "open me")
            print("Sent!")
            time.sleep(2)

        # Poll the message queue
        client.loop()

        gc.collect()
    except KeyboardInterrupt:
        client.disconnect()
        break
    except Exception as e:
        print("Failed to get data, retrying\n", e)
        reconnect()
        continue
