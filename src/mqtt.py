import paho.mqtt.client as mqtt
import json

class MQTTStreamer:
    def __init__(self, host="localhost", port=1883, topic="daq/live"):
        self.client = mqtt.Client()
        self.client.connect(host, port)
        self.topic = topic

    def send(self, data_dict):
        message = {
            **data_dict
        }
        self.client.publish(self.topic, json.dumps(message))

    def close(self):
        self.client.disconnect()