import sys
import json
import collections
import numpy as np

def parse_time(t_str):
    """Convert HH:MM:SS or MM:SS to timedelta."""
    parts = list(map(int, t_str.split(":")))
    seconds = parts[0]*3600 + parts[1]*60 + parts[2]
    return int(seconds * 1e9)

def main():
    # Load operation schedule
    with open(r"C:\Users\Lenovo\Desktop\CNC_Influx2\config\CAM_info.json", "r") as f:
        op_dict = {
            name: parse_time(time)
            for name, (time) in json.load(f).items()
        }

    # State variables
    prev_rms = None
    start_ts = None
    current_op = None
    op_id = 14
    prev_label = "idle"
    counter = 0
    output = []
    label = "idle"
    mean_buffer = collections.deque(maxlen=40)

    with open(r"C:\Users\Lenovo\Desktop\CNC_Influx2\notebooks\influx_simulated.txt", "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split(" ", 2)
            if len(parts) != 3:
                continue

            op_name = f"Op_{op_id}"
            op_time = int(op_dict[op_name])

            measurement_tag, fields, timestamp_str = parts

            # Extract Cu_rms value
            field_parts = fields.split(',')
            field_dict = {k: float(v) for k, v in (f.split('=') for f in field_parts)}
            cu_rms = field_dict.get('Cu_rms')
            if cu_rms is None:
                continue

            _, _, batch_id = measurement_tag.split(",")
            key, value = batch_id.split("=", 1)
            timestamp = int(value)

            mean_buffer.append(cu_rms)
            mean_val_rms = float(np.mean(mean_buffer))

            if prev_rms is None:
                prev_rms = mean_val_rms

            diff = abs(mean_val_rms - prev_rms)
            # Determine signal trend
            if diff > 0.05 and prev_label == "idle":
                #counter = 1
                label = "spindle_peak"

            elif prev_label == "spindle_peak" and not diff < 0.01:
                label = "spindle_peak"

            elif prev_label == "spindle_peak" and diff < 0.01:
                label = "idle"

            elif prev_label not in ["spindle_peak", "cutting"] and diff > 0.01:
                #start_ts = timestamp
                label = "cutting"
                #current_op = op_name

            elif prev_label == "cutting" and not diff  < 0.01:
                label = op_name

            elif prev_label == current_op and cu_rms < 2 and 1 < diff < 2 and start_ts and timestamp - start_ts >= op_time:
                label = "idle"
                if op_id < len(op_dict):
                    op_id += 1
                else:
                    op_id = 1

            else:
                label = prev_label

            prev_label = label
            prev_rms = cu_rms

            # Append labeled line
            measurement_tag += f",op={label}"
            new_line = f"{measurement_tag} {fields} {timestamp_str}"
            output.append(new_line)

    # Write to output file
    with open("influx_simulated_labeled.txt", "w") as f:
        for line in output:
            f.write(line + "\n")

if __name__ == "__main__":
    main()