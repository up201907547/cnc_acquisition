import sys
import os

log_file = "C:/Users/Lenovo/Desktop/CNC_Influx2/src/processor_log.txt"

def log(message):
    with open(log_file, "a") as f:
        f.write(message + "\n")

import sys
import numpy as np
from collections import deque

# Buffers and state
current_batch_id = None
batch_lines = []

cu_values = []
cu2_values = []
cu_star_values = []
fx, fy, fz = [], [], []
ax, ay, az = [], [], []

def parse_tags(meta_str):
    # Converts: "sensor_data,experiment_name=xyz,batch_id=123" → dict
    parts = meta_str.split(",")
    tags = {}
    for p in parts[1:]:  # skip measurement name
        k, v = p.split("=")
        tags[k] = v
    return tags

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue

    try:
        # Parse InfluxDB line protocol
        parts = line.split()
        if len(parts) != 3:
            continue  # malformed line

        meta_str, fields, timestamp = parts
        tags = parse_tags(meta_str)
        batch_id = tags.get("batch_id")

        if current_batch_id is None:
            current_batch_id = batch_id  # Initialize on first line

        # New batch detected → process and output previous batch
        if batch_id != current_batch_id:
            # Compute statistics
            mean_cu = np.mean(cu_values) if cu_values else 0.0
            mean_cu2 = np.mean(cu2_values) if cu2_values else 0.0
            rms_cu_star = np.sqrt(np.mean(np.square(cu_star_values))) if cu_star_values else 0.0
            f_res = np.mean(np.sqrt(np.array(fx)**2 + np.array(fy)**2 + np.array(fz)**2)) if fx else 0.0
            a_res = np.mean(np.sqrt(np.array(ax)**2 + np.array(ay)**2 + np.array(az)**2)) if ax else 0.0

            # Output line (use last timestamp)
            output_meta = f"sensor_data_processed,experiment_name={tags.get('experiment_name','unknown')},batch_id={current_batch_id}"
            field_pairs = {
                "Cu_mean": f"{mean_cu}",
                "Cu2_mean": f"{mean_cu2}",
                "Cu*_rms": f"{rms_cu_star}",
                "F_res": f"{f_res}",
                "A_res": f"{a_res}"
            }

            field_str = ",".join(f"{k}={v}" for k, v in field_pairs.items())
            last_timestamp = batch_lines[-1][1]
            output_line = f"{output_meta} {field_str} {last_timestamp}"
            print(output_line)
            print(f"sensor_live_processed {field_str} {last_timestamp}")
            sys.stdout.flush()

            # Reset buffers
            current_batch_id = batch_id
            batch_lines.clear()
            cu_values.clear()
            cu2_values.clear()
            cu_star_values.clear()
            fx.clear(); fy.clear(); fz.clear()
            ax.clear(); ay.clear(); az.clear()

        # Add current line to batch
        field_pairs = dict(kv.split("=") for kv in fields.split(","))

        if "Cu" in field_pairs:
            cu_values.append(float(field_pairs["Cu"]))
        if "Cu2" in field_pairs:
            cu2_values.append(float(field_pairs["Cu2"]))
        if "Cu*" in field_pairs:
            cu_star_values.append(float(field_pairs["Cu*"]))
        if "Fx" in field_pairs:
            fx.append(float(field_pairs["Fx"]))
            fy.append(float(field_pairs["Fy"]))
            fz.append(float(field_pairs["Fz"]))
        if "Ax" in field_pairs:
            ax.append(float(field_pairs["Ax"]))
            ay.append(float(field_pairs["Ay"]))
            az.append(float(field_pairs["Az"]))

        batch_lines.append((meta_str, timestamp))

    except Exception as e:
        print(f"# Error processing line: {e}", file=sys.stderr)
        sys.stderr.flush()
