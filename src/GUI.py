import os
import threading
import time
from datetime import datetime
from usb_daq import USB_DAQ
from mqtt import MQTTStreamer
import pyaudio
import wave
from tkinter import Tk, Frame, Button, Label, BooleanVar, Checkbutton, font, Entry, messagebox
import tkinter as tk
from tkinter import ttk
import sys
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.gridspec import GridSpec
from matplotlib.figure import Figure
import numpy as np
import queue
from matplotlib.animation import FuncAnimation
import pandas as pd
from influxdb_handler import DAQToInfluxDB
import json

base_dir = os.path.dirname(os.path.dirname(__file__))
print(base_dir)

class Main():
    def __init__(self):
        self.is_running = threading.Event()
        self.save_path = os.path.join(base_dir, r"data\Test_22_04")

        self.sampling_rate = 1000
        self.selected_sensors_daq = ["Current"]

        self.use_csv = False
        self.use_influx = True

        #GUI setup
        self.window = Tk()
        self.setup_window()
        self.create_main_frame()
        self.create_storage_selector_frame()
        self.create_command_frame()
        self.create_sensor_selection_frame()
        self.create_buttoms_frame()
        self.create_debug_frame()
        
        self.window.mainloop()

    def setup_window(self):
        self.window.title("Multisensorial Monitoring System")
        
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        window_width = 1000
        window_height = 400

        # Calculate x and y positions to center the window
        x_offset = (screen_width - window_width) // 2
        y_offset = (screen_height - window_height) // 2

        # Set window size and position
        self.window.geometry(f"{window_width}x{window_height}+{x_offset}+{y_offset}")
        self.window.minsize(window_width, window_height)

        self.window.rowconfigure(0, weight=1)
        self.window.columnconfigure(0, weight=1)
        

    def create_main_frame(self):
        self.main_frame = Frame(self.window, padx = 5, pady = 5)
        self.main_frame.grid(row=0, column=0, sticky = "nsew")
        self.main_frame.grid_rowconfigure([0,1,2,3], weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

    def create_storage_selector_frame(self):
        self.selector_frame = Frame(self.main_frame, padx=5, pady=5)
        self.selector_frame.grid(row=0, column=0, sticky="we")
        self.selector_frame.grid_columnconfigure([0,1], weight=1)

        # Label for the dropdown
        selector_label = tk.Label(self.selector_frame, text="Select Storage Type:", font=("Arial", 11))
        selector_label.grid(row=0, column=0, padx=(0, 0), sticky="e")

        # Dropdown variable and menu
        self.storage_option = tk.StringVar(value="InfluxDB")
        self.storage_option.trace_add("write", self.update_storage_flags)
        storage_menu = tk.OptionMenu(self.selector_frame, self.storage_option, "InfluxDB", "CSV")
        storage_menu.grid(row=0, column=1, sticky="w")

        self.stop_button = Button(self.selector_frame, text="Test", width=10, height=1, state="normal", command=self.test_bool)
        self.stop_button.grid(row=0, column=3, padx=0, pady=0, sticky="")

    def update_storage_flags(self, *args):
        selected = self.storage_option.get()
        self.use_csv = selected == "CSV"
        self.use_influx = selected == "InfluxDB"

    def test_bool(self):
        print(f"CSV: {self.use_csv} | InfluxDB: {self.use_influx}")         

    def create_debug_frame(self):
        # Create debug frame
        self.debug_frame = Frame(self.main_frame, padx=10, pady=10)
        self.debug_frame.grid(row=1, column=0, sticky="nsew")
        self.debug_frame.grid_rowconfigure(0, weight=1)
        self.debug_frame.grid_columnconfigure(0, weight=1)

        # Create label for text
        self.status_label = tk.Label(self.debug_frame, text="Not Working", font=("Arial", 12, "bold"), fg="white", bg="red",padx=900, pady=50)
        self.status_label.grid(row=1, column=0)


    def create_command_frame(self):
        self.command_frame = Frame(self.main_frame, padx = 5, pady = 5)
        self.command_frame.grid(row=2, column=0, sticky = "nsew")
        self.command_frame.grid_rowconfigure(0, weight=1)
        self.command_frame.grid_columnconfigure([0, 1], weight=1)

    def create_sensor_selection_frame(self):
        selection_frame = Frame(self.command_frame, padx=20, pady=0)
        selection_frame.grid(row=0, column=0, sticky="nsew")
        selection_frame.grid_rowconfigure(0, weight=1)
        selection_frame.grid_columnconfigure(0, weight=1)

        # Sensor checkboxes
        self.use_daq = BooleanVar(value=True)
        self.use_mic = BooleanVar(value=False)
        self.use_wifi = BooleanVar(value=False)
        self.use_mqtt = BooleanVar(value=False)

        # Attach trace to run setup_readers whenever a checkbox changes
        self.use_daq.trace_add("write", lambda *args: self.setup_readers())
        self.use_mic.trace_add("write", lambda *args: self.setup_readers())
        self.use_wifi.trace_add("write", lambda *args: self.setup_readers())
        self.use_mqtt.trace_add("write", lambda *args: self.setup_readers())

        label = Label(selection_frame, text="Select Sensors to Use:", font=("Helvetica", 14))
        label.grid(row=0, column=0, sticky="w", pady=(0, 0))

        self.daq_checkbox = Checkbutton(
            selection_frame, text="DAQ", variable=self.use_daq, font=("Helvetica", 12))
        self.daq_checkbox.grid(row=0, column=1, sticky="w")

        self.mic_checkbox = Checkbutton(
            selection_frame, text="MIC", variable=self.use_mic, font=("Helvetica", 12), state= "disabled")
        self.mic_checkbox.grid(row=0, column=2, sticky="w")

        self.wifi_checkbox = Checkbutton(
            selection_frame, text="WiFi ACCEL", variable=self.use_wifi, font=("Helvetica", 12), state= "disabled")
        self.wifi_checkbox.grid(row=0, column=3, sticky="w")

        self.mqtt_checkbox = Checkbutton(
            selection_frame, text="OTHER", variable=self.use_mqtt, font=("Helvetica", 12), state= "disabled")
        self.mqtt_checkbox.grid(row=0, column=4, sticky="w")

        #self.selection = Button(selection_frame, text="Select", font=("Helvetica", 14), width=10, height=1, command=self.setup_readers)
        #self.selection.grid(row=1, column=3, padx=0, pady=0, sticky="")

        # Label for displaying selected sensors
        self.selected_sensors_label = Label(selection_frame, text="Selected Sensors: None", font=("Helvetica", 12))
        self.selected_sensors_label.grid(row=1, column=0, columnspan=5, sticky="w", pady=(10, 0))

        if self.use_daq:
            self.setup_readers()

    def handle_daq_error(self, error):
        #print(f"DAQ error occurred: {error}")
        self.stop_acquisition()

    def setup_readers(self):
        # Collect selected sensors
        self.threads = []
        self.header = []
        self.selected_sensors = []
        if self.use_daq.get():
            with open(os.path.join(base_dir, r"config\daq_ch_map.json"), "r") as file:
                self.channel_mapping = json.load(file)

            for sensor in self.selected_sensors_daq:
                channels = self.channel_mapping.get(sensor)
                for channel_name, _ in channels.items():
                    self.header.append(channel_name)

            self.selected_sensors.append("DAQ")
            self.daq_data_queue = queue.Queue(maxsize=10000)
            self.mqtt_streamer = MQTTStreamer()
            self.influx_handler = DAQToInfluxDB(self.daq_data_queue, self.is_running, self.sampling_rate, self.mqtt_streamer)
            self.reader_DAQ = USB_DAQ(sampling_rate=self.sampling_rate, selected_sensors=self.selected_sensors_daq, data_queue = self.daq_data_queue, running_flag=self.is_running, influx_handler=self.influx_handler, error_callback=self.handle_daq_error)

        print(self.header)

        # Update the label with the selected sensors
        if self.selected_sensors:
            self.selected_sensors_label.config(text=f"Selected Sensors: {', '.join(self.selected_sensors)}")

    def create_buttoms_frame(self):
        button_frame = Frame(self.command_frame, padx = 0, pady = 0)
        button_frame.grid(row=0, column=1, sticky = "nsew")
        button_frame.grid_rowconfigure(0, weight=1)
        button_frame.grid_columnconfigure([0, 1, 2], weight=1)

        button_font = ("Helvetica", 14)

        self.start_button = Button(button_frame, text="Start", font=button_font, width=10, height=1, command=self.start_acquisition)
        self.start_button.grid(row=0, column=0, padx=0, pady=0, sticky="")

        self.stop_button = Button(button_frame, text="Stop", font=button_font, width=10, height=1, state="disabled", command=self.stop_acquisition)
        self.stop_button.grid(row=0, column=1, padx=0, pady=0, sticky="")

        self.restart_button = Button(button_frame, text="Restart", font=button_font, width=10, height=1, command=self.restart_program)
        self.restart_button.grid(row=0, column=2, padx=0, pady=0, sticky="")
    
        
    def logger(self, selected_sensors):
        return

    def start_acquisition(self):
        """Start the data acquisition process."""
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
        print(timestamp)
        #self.exp_name_folder = os.path.join(self.save_path, timestamp)
        #if not os.path.exists(self.exp_name_folder):
        #    os.makedirs(self.exp_name_folder)

        if "DAQ" in self.selected_sensors:
            if self.use_csv:
                self.csv_daq = os.path.join(self.exp_name_folder, "daq_data.csv")
                self.threads.append(threading.Thread(target=self.reader_DAQ.read_daq_sensor, args=(self.csv_daq, self.use_influx,), daemon=True))
            elif self.use_influx:
                self.threads.append(threading.Thread(target=self.reader_DAQ.read_daq_sensor, daemon=True))
                self.threads.append(threading.Thread(target=self.influx_handler.save_data, args=(timestamp, self.header,), daemon=True))

        self.is_running.set()

        for thread in self.threads:
            thread.start()

        self.starting_time = time.time()
        self.status_label.config(text="Acquiring Data", bg="green")

        self.restart_button.config(state="disabled")
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        
    def stop_acquisition(self):
        """Stop the data acquisition process."""
        self.is_running.clear()

        if "DAQ" in self.selected_sensors:
            self.reader_DAQ.stop_acquisition()
            self.influx_handler.close_connection()
            self.mqtt_streamer.close()

        total_time = time.time() - self.starting_time
        
        for thread in self.threads:
            thread.join()

        self.threads = []

        self.status_label.config(text="Finished Aquiring \n Press Restart for another run!", bg="blue")

        self.restart_button.config(state="normal")
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")

        print(f"Data acquisition stopped. Total time: {total_time:.2f} seconds")

    def restart_program(self):
        """Restart the current Python program."""
        python = sys.executable  # Path to the Python interpreter
        os.execl(python, python, *sys.argv)

if __name__ == "__main__":
    main = Main()