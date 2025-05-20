import threading
import queue
import time
import nidaqmx
from nidaqmx.system import System
from nidaqmx.constants import AcquisitionType
from nidaqmx.stream_readers import AnalogMultiChannelReader
from nidaqmx.constants import TerminalConfiguration
from nidaqmx.constants import Level, TriggerType
import numpy as np
import json
import collections
import pandas as pd
import os

base_dir = os.path.dirname(os.path.dirname(__file__))

def check_daq_connection():
    try:
        # Check if the device is available in the system
        system = nidaqmx.system.System.local()
        devices = system.devices
        device_names = [device.name for device in devices]
        
        if not any("NI-6210" in device_name for device_name in device_names):
            return "DAQ device not found."
        return None
    except Exception as e:
        return f"DAQ connection failed: {str(e)}"

class USB_DAQ:
    def __init__(self, sampling_rate, selected_sensors, data_queue, running_flag, handler=None, auto = False, error_callback=None):
        self.is_running = running_flag
        with open(os.path.join(base_dir, r"config\daq_ch_map.json"), "r") as file:
            self.channel_mapping = json.load(file)

        self.sampling_rate = sampling_rate
        self.selected_sensors = selected_sensors
        self.error_callback = error_callback
        self.auto = auto
    
        # Using deque instead of queue.Queue
        self.buffer_size = int(sampling_rate/10)
        #self.daq_data_deque = collections.deque(maxlen=self.buffer_size)
        self.daq_data_queue = data_queue

    def read_daq_sensor(self):
        """Internal method to acquire data and put it in the queue."""
        self.plot_data = []

        with nidaqmx.Task() as task:
            #self.count = 0
            self.header = []
            # Add channels based on selected sensors
            for sensor in self.selected_sensors:
                channels = self.channel_mapping.get(sensor)
                for channel_name, channel_id in channels.items():
                    if channel_id:
                        if sensor == "Force":
                            task.ai_channels.add_ai_voltage_chan(channel_id, terminal_config=TerminalConfiguration.RSE, min_val=-10, max_val=10)
                        elif sensor == "Current":
                            if channel_name == "CI":
                                task.ai_channels.add_ai_voltage_chan(channel_id, terminal_config=TerminalConfiguration.DIFF, min_val=-1, max_val=1)
                            else:
                                task.ai_channels.add_ai_voltage_chan(channel_id, terminal_config=TerminalConfiguration.DIFF, min_val=-10, max_val=10)
                        else:
                            task.ai_channels.add_ai_voltage_chan(channel_id, terminal_config=TerminalConfiguration.DIFF, min_val=-10, max_val=10)
                
            # Configure task timing
            task.timing.cfg_samp_clk_timing(
                rate=self.sampling_rate,
                sample_mode=AcquisitionType.CONTINUOUS,
                samps_per_chan=self.buffer_size
            )
            #task.timing.first_samp_clk_timescale = nidaqmx.constants.TimeUnits.NANOSECONDS
            #first = task.timing.first_samp_timestamp_val

            # Create the reader and buffer
            reader = AnalogMultiChannelReader(task.in_stream)
            num_channels = len(task.ai_channels)
            buffer = np.zeros((num_channels, self.buffer_size))

            if not self.auto:
                print("Manual")
                try:
                    while self.is_running.is_set():
                        # Read data and put it in the queue
                        reader.read_many_sample(buffer, self.buffer_size)
                        batch_id = time.time_ns()

                        data_with_id = {
                            "data": buffer.copy(),
                            "batch_id": batch_id
                        }
                        
                        self.daq_data_queue.put(data_with_id, timeout=1)


                        # Save data to file periodically
                        #self.daq_data_queue.put(buffer.copy(), timeout=1)
                        #self.count += len(buffer[0].copy())

                        if not self.is_running.is_set():
                            break

                except nidaqmx.errors.DaqReadError as e:
                    #self.stop_acquisition()
                    print("DaqReadError encountered:", e)

                    if self.error_callback:
                        self.error_callback(e)
            else:
                #with nidaqmx.Task() as trig_task:
                    
                    #trig_task.do_channels.add_do_chan("/NI-6210/PFI6")
                    #previous_state = False
                
                print("Auto")                

                task.triggers.start_trigger.trig_type = TriggerType.DIGITAL_EDGE
                task.triggers.start_trigger.dig_edge_src = "/NI-6210/PFI4"
                task.triggers.start_trigger.dig_edge_edge = nidaqmx.constants.Edge.RISING

                task.triggers.pause_trigger.trig_type = TriggerType.DIGITAL_LEVEL
                task.triggers.pause_trigger.dig_lvl_src = "/NI-6210/PFI5"
                task.triggers.pause_trigger.dig_lvl_when = Level.HIGH

                task.start()
                try:
                    while self.is_running.is_set():
                        # Read data and put it in the queue
                        reader.read_many_sample(buffer, self.buffer_size)
                            
                        # Save data to file periodically
                        self.daq_data_queue.put(buffer.copy(), timeout=1)
                        #self.count += len(buffer[0].copy())

                            #current_state = trig_task.read()
                            #print("Current state:", current_state, "Previous state:", previous_state)
                            #if current_state and not previous_state:  # rising edge
                            #    self.stop_acquisition()
                            #    task.stop()

                        if not self.is_running.is_set():
                            break

                except nidaqmx.errors.DaqReadError as e:
                        #self.stop_acquisition()
                        print("DaqReadError encountered:", e)

                        if self.error_callback:
                            self.error_callback(e)
                finally:
                    task.stop()

    def stop_acquisition(self):
        """Stop data acquisition and save data."""
        self.is_running.clear()
        #print(self.count)
