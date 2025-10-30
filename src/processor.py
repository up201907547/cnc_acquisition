import sys
import os

log_file = "C:/Users/Lenovo/Desktop/CNC_Influx2/src/processor_log.txt"

def log(message):
    with open(log_file, "a") as f:
        f.write(message + "\n")

"""
def main():
    log("Processor started")
    for line in sys.stdin:
        line = line.strip()
        if line:
            log(f"Received: {line}")
            # Echo back the line (or modify it as needed)
            print(line)
            sys.stdout.flush()

if __name__ == "__main__":
    main()

"""
import sys
import numpy as np
from collections import deque

rms_buf = deque(maxlen=400)  # RMS window size
mean_buf = deque(maxlen=400)  # Mean window size
sum_sq = 0.0
sum_mean = 0.0

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue

    try:
        # Parse InfluxDB line protocol
        parts = line.split()
        meta, fields, timestamp = parts

        field_pairs = dict(kv.split("=") for kv in fields.split(","))

        if "Cu*" in field_pairs:
            val = float(field_pairs["Cu*"])

            # Update RMS buffer
            if len(rms_buf) == rms_buf.maxlen:
                oldest = rms_buf.popleft()
                sum_sq -= oldest * oldest
            rms_buf.append(val)
            sum_sq += val * val

            # Calculate RMS
            if len(rms_buf) == rms_buf.maxlen:
                rms = np.sqrt(sum_sq / len(rms_buf))
            else:
                rms = 0.0

            del field_pairs["Cu*"]
            field_pairs["Cu*_rms"] = f"{rms}"

        if "Cu" in field_pairs:
            # Update Mean buffer
            if len(mean_buf) == mean_buf.maxlen:
                oldest = mean_buf.popleft()
                sum_mean -= oldest  # subtract oldest value from sum

            mean_buf.append(val)
            sum_mean += val  # add new value to sum

            # Calculate mean
            if len(mean_buf) == mean_buf.maxlen:
                mean = sum_mean / len(mean_buf)
            else:
                mean = 0.0

            del field_pairs["Cu"]
            field_pairs["Cu_mean"] = f"{mean}"

        if "Fx" in field_pairs:
            val_fx = float(field_pairs["Fx"])
            val_fy = float(field_pairs["Fy"])
            val_fz = float(field_pairs["Fz"])

            val = np.sqrt(val_fx * val_fx + val_fy * val_fy + val_fz * val_fz)
            del field_pairs["Fx"]
            del field_pairs["Fy"]
            del field_pairs["Fz"]
            field_pairs["F_res"] = f"{val}"

        if "Ax" in field_pairs:
            val_fx = float(field_pairs["Ax"])
            val_fy = float(field_pairs["Ay"])
            val_fz = float(field_pairs["Az"])

            val = np.sqrt(val_fx * val_fx + val_fy * val_fy + val_fz * val_fz)
            del field_pairs["Ax"]
            del field_pairs["Ay"]
            del field_pairs["Az"]
            field_pairs["A_res"] = f"{val}"

        # Reconstruct line protocol string
        field_str = ",".join(f"{k}={v}" for k, v in field_pairs.items())
        output_line = f"{meta} {field_str} {timestamp}"
        output_live = f"sensor_live_processed {field_str} {timestamp}"
        #log(f"Sent: {output_line}")
        print(output_line)
        print(output_live)
        sys.stdout.flush()

    except Exception as e:
        print(f"# Error processing line: {e}", file=sys.stderr)
        sys.stderr.flush()

