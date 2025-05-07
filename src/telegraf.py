import socket
import time
import queue
from influxdb_client import InfluxDBClient
import csv
from collections import defaultdict
import os

class DAQToTelegraf:
    def __init__(self, data_queue, is_running, sampling_rate):
        self.is_running = is_running
        self.daq_data_queue = data_queue
        self.SAMPLE_INTERVAL_NS = int(1e9 / sampling_rate)
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.telegraf_address = ("127.0.0.1", 8094)

    def save_data(self, experiment_name, channel_names):
        self.count = 0
        base_time = time.time_ns()
        while self.is_running.is_set():
            try:
                buffer = self.daq_data_queue.get(timeout=1)
                if not self.is_running.is_set():
                    break

                for sample in buffer.T:
                    self.count += 1
                    point_time = base_time + self.count * self.SAMPLE_INTERVAL_NS
                    fields = []

                    for i, value in enumerate(sample):
                        field_name = channel_names[i]
                        field_value = float(value)
                        fields.append(f"{field_name}={field_value}")

                    line = f"sensor_data,experiment_name={experiment_name} {','.join(fields)} {point_time}"
                    self.udp_socket.sendto(line.encode(), self.telegraf_address)

                    line = f"sensor_live {','.join(fields)} {point_time}"
                    self.udp_socket.sendto(line.encode(), self.telegraf_address)

            except queue.Empty:
                continue
    
    def stop_send_data(self):
        self.is_running.clear()
        print(self.count)

    def close_connection(self):
        self.udp_socket.close()


def save_csv_influx(experiment_name, file):
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
            timestamp = record.get_time().isoformat()
            field = record.get_field()
            value = record.get_value()
            pivoted_data[timestamp][field] = value

    # Collect all field names for header
    all_fields = set()
    for fields in pivoted_data.values():
        all_fields.update(fields.keys())
    sorted_fields = sorted(all_fields)

    # Write CSV
    with open(os.path.join(file, "daq_data.csv"), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Time"] + sorted_fields)  # Header

        for timestamp in sorted(pivoted_data):
            row = [timestamp]
            for field in sorted_fields:
                row.append(pivoted_data[timestamp].get(field, ""))
            writer.writerow(row)
                

if __name__ == "__main__":
    save_csv_influx("2025-05-07_10-40-32")