import sys
import os

log_file = "C:/Users/Lenovo/Desktop/CNC_Influx2/src/processor_log.txt"

def log(message):
    with open(log_file, "a") as f:
        f.write(message + "\n")

import sys
import numpy as np
import math
from collections import deque

# Buffers and state
current_batch_id = None
batch_lines = None

count = 0
sum_cu_values = 0.0
sum_cu2_values = 0.0
sum_cu_star_values = 0.0
sum_fr = 0.0
sum_ar = 0.0

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
            mean_cu = sum_cu_values / count
            mean_cu2 = sum_cu2_values / count
            rms_cu_star = math.sqrt(sum_cu_star_values / count)
            f_res = sum_fr/count
            a_res = sum_ar/count

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
            last_timestamp = batch_lines
            output_line = f"{output_meta} {field_str} {last_timestamp}"
            print(output_line)
            print(f"sensor_live_processed {field_str} {last_timestamp}")
            sys.stdout.flush()

            # Reset buffers
            current_batch_id = batch_id
            batch_lines.clear()
            count = 0
            sum_cu_values = 0.0
            sum_cu2_values = 0.0
            sum_cu_star_values = 0.0
            sum_fr = 0.0
            sum_ar = 0.0

        # Add current line to batch
        field_pairs = dict(kv.split("=") for kv in fields.split(","))

        if "Cu" in field_pairs:
            sum_cu_values += float(field_pairs["Cu"]) 
        if "Cu2" in field_pairs:
            sum_cu2_values += float(field_pairs["Cu2"])
        if "Cu*" in field_pairs:
            sum_cu_star_values += float(field_pairs["Cu*"]) * float(field_pairs["Cu*"])
        if "Fx" in field_pairs:
            sum_fr += math.sqrt(float(field_pairs["Fx"]) * float(field_pairs["Fx"]) + float(field_pairs["Fy"]) * float(field_pairs["Fy"]) + float(field_pairs["Fz"]) * float(field_pairs["Fz"]))
        if "Ax" in field_pairs:
            sum_ar += math.sqrt(float(field_pairs["Ax"]) * float(field_pairs["Ax"]) + float(field_pairs["Ay"]) * float(field_pairs["Ay"]) + float(field_pairs["Az"]) * float(field_pairs["Az"]))

        count += 1

        batch_lines = timestamp

    except Exception as e:
        print(f"# Error processing line: {e}", file=sys.stderr)
        sys.stderr.flush()
