import numpy as np
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import time
from usb_daq import USB_DAQ
import threading
import queue

# InfluxDB connection parameters
INFLUXDB_URL = "http://localhost:8086"
INFLUXDB_TOKEN = "dVUcOtQscCWIT96i5vBgA9qWHDDKQ6OhOwTLcOzXPRAu6Xsbh-2MCVL6oV7_p9Y4Y7nHtyVes5MkxlQMClnmUw=="
INFLUXDB_ORG = "FEUP"
INFLUXDB_BUCKET = "CNC data"

class DAQToInfluxDB:
    def __init__(self, data_queue, is_running, sampling_rate, live_streamer):
        self.is_running = is_running
        self.influx_client = InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG
        )
        self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
        self.daq_data_queue = data_queue
        self.SAMPLE_INTERVAL_NS = int(1e9 / sampling_rate)
        self.live_streamer = live_streamer

    def save_data(self, experiment_name, channel_names):
        self.count = 0
        base_time = time.time_ns()
        while self.is_running.is_set():
            try:
                buffer = self.daq_data_queue.get(timeout=1)
                points = []
                #base_time = time.time_ns()
                data_dict = {}

                if not self.is_running.is_set():
                    break

                for sample in buffer.T:
                    self.count += 1
                    point_time = base_time + self.count * self.SAMPLE_INTERVAL_NS

                    point = Point("sensor_data") \
                        .tag("experiment name", experiment_name) \
                        .time(point_time)
                    for i, value in enumerate(sample):
                        field_name = channel_names[i]
                        field_value = float(value)
                        point = point.field(field_name, field_value)
                        data_dict[field_name] = field_value
                    points.append(point)

                    # Send to Grafana Live
                    if self.live_streamer:
                        self.live_streamer.send(data_dict)
                self.write_api.write(bucket=INFLUXDB_BUCKET, record=points)
                    
                
            except queue.Empty:
                continue

    def close_connection(self):
        """
        Close the InfluxDB client connection.
        """
        self.write_api.close()  # Close the write API
        self.influx_client.close()  # Close the client connection
        self.is_running.clear()
        print(self.count)

    