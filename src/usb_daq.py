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
import logging

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
    def __init__(self, sampling_rate, selected_sensors, data_queue, running_flag, handler=None, auto = False, error_callback=None, timed=False, time_limit=60, start_callback=None, stop_callback=None):
        self.is_running = running_flag
        with open(os.path.join(base_dir, r"config\daq_ch_map.json"), "r") as file:
            self.channel_mapping = json.load(file)

        self.sampling_rate = sampling_rate
        self.selected_sensors = selected_sensors
        self.error_callback = error_callback
        self.auto = auto
        self.timed = timed
        self.time_limit = time_limit
        self.start_callback = start_callback
        self.stop_callback = stop_callback
    
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
                            if channel_name == "Cu*":
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
                first_batch = True
                try:
                    while self.is_running.is_set():
                        # Read data and put it in the queue
                        reader.read_many_sample(buffer, self.buffer_size)

                        if first_batch:
                            first_batch = False
                            self.start_time = time.time()
                            if self.start_callback:
                                self.start_callback()

                        # Stop if time limit exceeded
                        if time.time() - self.start_time >= self.time_limit and self.timed:
                            logging.info("Acquisition stopped due to time limit.")
                            break

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
                    logging.info(f"Total Time DAQ: {time.time() - self.start_time} s")
                    if self.stop_callback:
                        self.stop_callback()
                    if self.is_running.is_set():
                        self.error_callback(None)
                    

                except nidaqmx.errors.DaqReadError as e:
                    #self.stop_acquisition()
                    print("DaqReadError encountered:", e)
                    if self.error_callback:
                        self.error_callback(e)
            else:
                print("Auto")
                if self.stop_callback:
                        self.stop_callback()      

                task.triggers.start_trigger.trig_type = TriggerType.DIGITAL_EDGE
                task.triggers.start_trigger.dig_edge_src = "/NI-6210/PFI0"
                task.triggers.start_trigger.dig_edge_edge = nidaqmx.constants.Edge.RISING

                #task.triggers.pause_trigger.trig_type = TriggerType.DIGITAL_LEVEL
                #task.triggers.pause_trigger.dig_lvl_src = "/NI-6210/PFI5"
                #task.triggers.pause_trigger.dig_lvl_when = Level.HIGH
                first_batch = True

                stop_task = nidaqmx.Task()
                stop_task.di_channels.add_di_chan("/NI-6210/PFI1")

                task.start()
                try:
                    while self.is_running.is_set():

                        # Read data and put it in the queue
                        reader.read_many_sample(buffer, self.buffer_size, timeout=360.0)

                        if stop_task.read():  # Stop if digital pin goes HIGH
                            logging.info("Stopped by digital input")
                            break

                        if first_batch:
                            first_batch = False
                            self.start_time = time.time()
                            if self.start_callback:
                                self.start_callback()

                        if time.time() - self.start_time >= self.time_limit and self.timed:
                            logging.info("Acquisition stopped due to time limit.")
                            break

                        batch_id = time.time_ns()

                        data_with_id = {
                            "data": buffer.copy(),
                            "batch_id": batch_id
                        }
                        
                        self.daq_data_queue.put(data_with_id, timeout=1)

                        if not self.is_running.is_set():
                            break

                    logging.info(f"Total Time DAQ: {time.time() - self.start_time} s")

                    task.stop()
                    stop_task.close()
                    #if self.stop_callback:
                    #    self.stop_callback()

                    if self.is_running.is_set():
                        self.error_callback(None)
                    

                except nidaqmx.errors.DaqReadError as e:
                        #self.stop_acquisition()
                        print("DaqReadError encountered:", e)
                        if self.error_callback:
                            self.error_callback(e)
                    

    def stop_acquisition(self):
        """Stop data acquisition and save data."""
        self.is_running.clear()
