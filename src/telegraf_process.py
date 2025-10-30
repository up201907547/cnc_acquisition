import socket
import time
import queue
from influxdb_client import InfluxDBClient
import csv
from collections import defaultdict
import os
import json
import collections
import numpy as np

base_dir = os.path.dirname(os.path.dirname(__file__))

class DAQToTelegraf:
    def __init__(self, data_queue, is_running, sampling_rate, rms_window_ms=40):
        
        self.is_running = is_running
        self.daq_data_queue = data_queue
        self.SAMPLE_INTERVAL_NS = int(1e9 / sampling_rate)
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.telegraf_address = ("127.0.0.1", 8094)

        with open( os.path.join(base_dir, r"config\uinits_conv.json"), 'r') as f:
            self.conversion_factors = json.load(f)

        self.channel_buffers = {}
        self.rms_window_samples = int(sampling_rate * (rms_window_ms / 1000))
        self.rms_buf = collections.deque(maxlen=self.rms_window_samples)

    def save_data(self, experiment_name, channel_names):
        self.count_global = 0
        base_time = time.time_ns()
        while self.is_running.is_set():
            try:
                queued = self.daq_data_queue.get(timeout=1)
                buffer = queued["data"]
                batch_id = queued["batch_id"]
                self.count = 0

                if not self.is_running.is_set():
                    break

                for sample in buffer.T:
                    self.count += 1
                    self.count_global += 1
                    point_time = base_time + self.count_global * self.SAMPLE_INTERVAL_NS
                    fields = []

                    for i, value in enumerate(sample):
                        field_name = channel_names[i]
                        factor = self.conversion_factors.get(field_name, 1.0)
                        field_value = float(value) * factor

                        if field_name == 'Cu*':
                            self.rms_buf.append(field_value)
                            if len(self.rms_buf) == self.rms_window_samples:
                                rms_val = float(np.sqrt(np.mean(np.square(self.rms_buf))))
                                fields.append(f"{field_name}_rms={rms_val}")
                            else:
                                fields.append(f"{field_name}_rms={0.0}")
                        elif field_name == 'Cu':
                            self.rms_buf.append(field_value)
                            mean_val = float(np.mean(self.rms_buf))
                            fields.append(f"{field_name}_mean={mean_val}")


                        fields.append(f"{field_name}={field_value}")

                    line = f"sensor_data,experiment_name={experiment_name},batch_id={batch_id} {','.join(fields)} {point_time}"
                    self.udp_socket.sendto(line.encode(), self.telegraf_address)

                    line = f"sensor_live {','.join(fields)} {point_time}"
                    self.udp_socket.sendto(line.encode(), self.telegraf_address)

            except queue.Empty:
                continue
    
    def stop_send_data(self):
        self.is_running.clear()
        print(self.count_global)

    def close_connection(self):
        self.udp_socket.close()


def save_csv_influx_old(experiment_name, file):
    client = InfluxDBClient(
    url="http://localhost:8086",
    token="dVUcOtQscCWIT96i5vBgA9qWHDDKQ6OhOwTLcOzXPRAu6Xsbh-2MCVL6oV7_p9Y4Y7nHtyVes5MkxlQMClnmUw==",
    org="FEUP"
    )

    query = f'''
    from(bucket: "CNC data")
    |> range(start: 0)
    |> filter(fn: (r) => r["_measurement"] == "sensor_data")
    |> filter(fn: (r) => r["experiment_name"] == "{experiment_name}")
    '''

    tables = client.query_api().query(query)

    # Dictionary: timestamp -> {field_name: value}
    pivoted_data = defaultdict(dict)

    for table in tables:
        for record in table.records:
            timestamp = record.get_time().timestamp()
            field = record.get_field()
            value = record.get_value()
            batch_id = record['batch_id']
            pivoted_data[timestamp][field] = value
            pivoted_data[timestamp]['Batch_id'] = batch_id

    # Collect all field names for header
    all_fields = set()
    for fields in pivoted_data.values():
        all_fields.update(fields.keys())

    sorted_data_fields = sorted(f for f in all_fields if f != "Batch_id")
    sorted_fields = ["Batch_id"] + sorted_data_fields

    print(sorted_fields)

    # Write CSV
    with open(os.path.join(file, "daq_data.csv"), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Time"] + sorted_fields)  # Header

        for timestamp in sorted(pivoted_data):
            row = [timestamp]  # Start with timestamp and batch_id
            for field in sorted_fields:
                row.append(pivoted_data[timestamp].get(field, ""))
            writer.writerow(row)
                
def save_csv_influx(experiment_name, file):
    client = InfluxDBClient(
    url="http://localhost:8086",
    token="dVUcOtQscCWIT96i5vBgA9qWHDDKQ6OhOwTLcOzXPRAu6Xsbh-2MCVL6oV7_p9Y4Y7nHtyVes5MkxlQMClnmUw==",
    org="FEUP"
    )

    # Query distinct batch_ids for the experiment
    batch_id_query = f'''
    import "influxdata/influxdb/schema"
    from(bucket: "CNC data")
    |> range(start: 0)
    |> filter(fn: (r) => r["_measurement"] == "sensor_data")
    |> filter(fn: (r) => r["experiment_name"] == "{experiment_name}")
    |> keep(columns: ["batch_id"])
    |> group(columns: ["batch_id"])
    |> distinct(column: "batch_id")
    |> drop(columns: ["batch_id"])
    '''

    batch_id_tables = client.query_api().query(batch_id_query)
    batch_ids = set()

    for table in batch_id_tables:
        for record in table.records:
            batch_ids.add(record["_value"])

    all_rows = []

    for batch_id in batch_ids:
        #print(f"Fetching batch {batch_id}")

        query = f'''
            from(bucket: "CNC data")
            |> range(start: 0)
            |> filter(fn: (r) => r["_measurement"] == "sensor_data")
            |> filter(fn: (r) => r["experiment_name"] == "{experiment_name}")
            |> filter(fn: (r) => r["batch_id"] == "{batch_id}")
        '''

        tables = client.query_api().query(query)

        pivoted_data = defaultdict(dict)

        for table in tables:
            for record in table.records:
                timestamp = record.get_time().timestamp()
                field = record.get_field()
                value = record.get_value()
                pivoted_data[timestamp][field] = value
                pivoted_data[timestamp]['Batch_id'] = batch_id

        all_rows.extend([
            {"Time": ts, **fields}
            for ts, fields in pivoted_data.items()
        ])

    # Get all field names
    all_fields = set()
    for row in all_rows:
        all_fields.update(row.keys())

    sorted_data_fields = sorted(f for f in all_fields if f != "Batch_id" and f != "Time")
    sorted_fields = ["Time", "Batch_id"] + sorted_data_fields

    # Write to CSV
    with open(os.path.join(file, "daq_data.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=sorted_fields)
        writer.writeheader()
        for row in sorted(all_rows, key=lambda r: r['Time']):
            writer.writerow(row)

if __name__ == "__main__":
    save_csv_influx("2025-05-27_10-02-16", r"C:\Users\Lenovo\Desktop\CNC_Influx2")