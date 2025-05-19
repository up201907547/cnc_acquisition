import os
import threading
import time
from datetime import datetime
from usb_daq import USB_DAQ
from old.mqtt import MQTTStreamer
from init_server_grafana import InitServer
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
from telegraf import DAQToTelegraf, save_csv_influx
import json

base_dir = os.path.dirname(os.path.dirname(__file__))

class Main():
    def __init__(self):
        self.is_running = threading.Event()
        self.save_path = os.path.join(base_dir, r"data\Test_07_05")

        self.sampling_rate = 1000
        self.selected_sensors_daq = ["Current"]

        self.use_csv = False
        self.use_influx = True
        self.manual = True
        self.auto = False

        self.app = InitServer()

        #GUI setup
        self.window = Tk()
        self.setup_window()
        self.create_main_frame()
        self.create_storage_selector_frame()
        self.create_command_frame()
        self.create_sensor_selection_frame()
        self.create_buttoms_frame()
        self.create_debug_frame()


        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.window.mainloop()

    def setup_window(self):
        self.window.title("Multisensorial Monitoring System")
        
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        window_width = 300
        window_height = 400

        # Calculate x and y positions to center the window
        x_offset = screen_width - window_width - 10
        y_offset = screen_height - window_height - 70

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
        self.selector_frame.grid_rowconfigure([0,1], weight=1)

        # Label for the dropdown
        selector_label = tk.Label(self.selector_frame, text="Storage Mode:", font=("Arial", 11))
        selector_label.grid(row=0, column=0, padx=(0, 0), sticky="e")

        # Dropdown variable and menu
        self.storage_option = tk.StringVar(value="InfluxDB")
        self.storage_option.trace_add("write", self.update_storage_flags)
        storage_menu = tk.OptionMenu(self.selector_frame, self.storage_option, "InfluxDB", "CSV")
        storage_menu.grid(row=0, column=1, sticky="w")

        # Label for the dropdown
        selector_label = tk.Label(self.selector_frame, text="Operation Mode:", font=("Arial", 11))
        selector_label.grid(row=1, column=0, padx=(0, 0), sticky="e")

        # Dropdown variable and menu
        self.op_option = tk.StringVar(value="Manual")
        self.op_option.trace_add("write", self.update_op_flags)
        storage_menu = tk.OptionMenu(self.selector_frame, self.op_option, "Manual", "Auto")
        storage_menu.grid(row=1, column=1, sticky="w")

        self.test_button = Button(self.selector_frame, text="Test", width=10, height=1, state="normal", command=self.test_bool)
        self.test_button.grid(row=0, column=3, padx=0, pady=0, sticky="")

    def update_storage_flags(self, *args):
        selected = self.storage_option.get()
        self.use_csv = selected == "CSV"
        self.use_influx = selected == "InfluxDB"
        self.setup_readers()

    def update_op_flags(self, *args):
        selected = self.op_option.get()
        self.manual = selected == "Manual"
        self.auto = selected == "Auto"
        self.setup_readers()

    def test_bool(self):
        print(f"Manual: {self.manual} | Auto: {self.auto}")         

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

        label = Label(selection_frame, text="Select Sensors:", font=("Helvetica", 14))
        label.grid(row=0, column=0, sticky="w", pady=(0, 0))

        self.daq_checkbox = Checkbutton(
            selection_frame, text="DAQ", variable=self.use_daq, font=("Helvetica", 12))
        self.daq_checkbox.grid(row=1, column=0, sticky="w")

        self.wifi_checkbox = Checkbutton(
            selection_frame, text="WiFi ACCEL", variable=self.use_wifi, font=("Helvetica", 12), state= "normal")
        self.wifi_checkbox.grid(row=2, column=0, sticky="w")

        self.mic_checkbox = Checkbutton(
            selection_frame, text="MIC", variable=self.use_mic, font=("Helvetica", 12), state= "disabled")
        self.mic_checkbox.grid(row=3, column=0, sticky="w")

        self.mqtt_checkbox = Checkbutton(
            selection_frame, text="OTHER", variable=self.use_mqtt, font=("Helvetica", 12), state= "disabled")
        self.mqtt_checkbox.grid(row=4, column=0, sticky="w")

        #self.selection = Button(selection_frame, text="Select", font=("Helvetica", 14), width=10, height=1, command=self.setup_readers)
        #self.selection.grid(row=1, column=3, padx=0, pady=0, sticky="")

        # Label for displaying selected sensors
        #self.selected_sensors_label = Label(selection_frame, text="Selected Sensors: None", font=("Helvetica", 12))
        #self.selected_sensors_label.grid(row=1, column=0, columnspan=5, sticky="w", pady=(10, 0))

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
            self.telegraf_handler = DAQToTelegraf(self.daq_data_queue, self.is_running, self.sampling_rate)
            self.reader_DAQ = USB_DAQ(sampling_rate=self.sampling_rate, selected_sensors=self.selected_sensors_daq, data_queue = self.daq_data_queue, running_flag=self.is_running, handler=self.telegraf_handler, auto = self.auto, error_callback=self.handle_daq_error)

        if self.use_wifi.get():
            return print("Streak sensor will be recorded!")

        # Update the label with the selected sensors
        #if self.selected_sensors:
        #    self.selected_sensors_label.config(text=f"Selected Sensors: {', '.join(self.selected_sensors)}")

    def create_buttoms_frame(self):
        button_frame = Frame(self.command_frame, padx = 0, pady = 0)
        button_frame.grid(row=0, column=1, sticky = "nsew")
        button_frame.grid_rowconfigure([0, 1, 2], weight=1)
        button_frame.grid_columnconfigure(0, weight=1)

        button_font = ("Helvetica", 14)

        self.start_button = Button(button_frame, text="Start", font=button_font, width=10, height=1, command=self.start_acquisition)
        self.start_button.grid(row=0, column=0, padx=0, pady=0, sticky="")

        self.stop_button = Button(button_frame, text="Stop", font=button_font, width=10, height=1, state="disabled", command=self.stop_acquisition)
        self.stop_button.grid(row=1, column=0, padx=0, pady=0, sticky="")

        self.restart_button = Button(button_frame, text="Restart", font=button_font, width=10, height=1, command=self.restart_program)
        self.restart_button.grid(row=2, column=0, padx=0, pady=0, sticky="")
    
        
    def logger(self, selected_sensors):
        return

    def start_acquisition(self):
        """Start the data acquisition process."""
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
        print(timestamp)
        print(self.header)
        self.exp_name = timestamp

        if "DAQ" in self.selected_sensors:
            #if self.auto:
                #self.threads.append(threading.Thread(target=self.reader_DAQ.watch_for_stop_signal))
            self.threads.append(threading.Thread(target=self.reader_DAQ.read_daq_sensor, daemon=True))
            self.threads.append(threading.Thread(target=self.telegraf_handler.save_data, args=(timestamp, self.header,), daemon=True))

        if "WIFI ACCEL" in self.selected_sensors:
            return
        
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
            self.telegraf_handler.stop_send_data()

        total_time = time.time() - self.starting_time
        
        for thread in self.threads:
            thread.join()

        self.threads = []

        if self.use_csv:
            self.exp_name_folder = os.path.join(self.save_path, self.exp_name)
            if not os.path.exists(self.exp_name_folder):
                os.makedirs(self.exp_name_folder)

            time.sleep(1)
            save_csv_influx(self.exp_name, self.exp_name_folder)

        self.status_label.config(text="Finished Aquiring \n Press Restart for another run!", bg="blue")

        self.restart_button.config(state="normal")
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")

        print(f"Data acquisition stopped. Total time: {total_time:.2f} seconds")

    def restart_program(self):
        """Restart the current Python program."""
        python = sys.executable  # Path to the Python interpreter
        self.app.stop()
        os.execl(python, python, *sys.argv)

    def on_close(self):
        """Handle the window close event."""
        print("Closing the application...")
        self.telegraf_handler.close_connection()
        self.window.quit()
        self.app.close()

        time.sleep(1)

if __name__ == "__main__":
    main = Main()