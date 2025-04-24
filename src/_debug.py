import os
import threading
import time
from datetime import datetime
from usb_daq import USB_DAQ
from usb_mic import USB_MIC
from wifi_accel import WIFI_ACCEL
import pyaudio
import wave

class Main():
    def __init__(self):
        self.is_running = threading.Event()

        self.reader_DAQ = USB_DAQ(sampling_rate=1000, selected_sensors=["Vibration"])
        self.reader_MIC = USB_MIC()
        self.reader_wifi = WIFI_ACCEL()

        self.save_path = r'C:\Users\Lenovo\Desktop\CNC_SyncSensors_APP\data'

        self.threads = [
            threading.Thread(target=self.reader_DAQ.read_daq_sensor, args=(self.is_running,)),
            threading.Thread(target=self.reader_MIC.read_usb_mic, args=(self.is_running,)),
            threading.Thread(target=self.reader_wifi.read_wifi_sensor, args=(self.is_running,)),
            threading.Thread(target=self.logger),
        ]

        self.exp_name_folder = ''
        self.p = self.reader_MIC.p

        self.daq_data_queue = self.reader_DAQ.daq_data_queue
        self.mic_data_queue = self.reader_MIC.mic_data_queue
        self.wifi_data_queue = self.reader_wifi.wifi_data_queue
    
    def logger(self):

        file_daq = open(f"{self.exp_name_folder}/daq_data.csv", "a")

        file_audio =  wave.open(f"{self.exp_name_folder}/audio.wav", 'wb')
        file_audio.setnchannels(1)
        file_audio.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
        file_audio.setframerate(44100)

        file_wifi = open(f"{self.exp_name_folder}/wifi_data.csv", "a")

        try:
            while self.is_running.is_set():
                timestamp_daq, data_daq = self.daq_data_queue.get()
                file_daq.write(f"{timestamp_daq},{data_daq}\n")
                file_daq.flush()

                frames_audio = self.mic_data_queue.get()
                file_audio.writeframes(frames_audio)

                timestamp_wifi, data_wifi = self.wifi_data_queue.get()
                file_wifi.write(f"{timestamp_wifi},{data_wifi}\n")
                file_wifi.flush()

            while not self.daq_data_queue.empty():
                timestamp_daq, data_daq = self.daq_data_queue.get()
                file_daq.write(f"{timestamp_daq},{data_daq}\n")
                file_daq.flush()

            while not self.mic_data_queue.empty():
                frames_audio = self.mic_data_queue.get()
                file_audio.writeframes(frames_audio)

            while not self.wifi_data_queue.empty():
                timestamp_wifi, data_wifi = self.wifi_data_queue.get()
                file_wifi.write(f"{timestamp_wifi},{data_wifi}\n")
                file_wifi.flush()

        except KeyboardInterrupt:
            pass
        finally:
                file_daq.close()
                file_audio.close()
                file_wifi.close()

    def start_acquisition(self):
        """Start the data acquisition process."""
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
        self.exp_name_folder = os.path.join(self.save_path, timestamp)
        if not os.path.exists(self.exp_name_folder):
            os.makedirs(self.exp_name_folder)

        self.is_running.set()

        self.starting_time = time.time()
        
        for thread in self.threads:
            thread.start()

    def stop_acquisition(self):
        """Stop the data acquisition process."""
        self.is_running.clear()
        total_time = time.time() - self.starting_time
        
        for thread in self.threads:
            thread.join()

        print(f"Data acquisition stopped. Total time: {total_time:.2f} seconds")


if __name__ == "__main__":
    main = Main()

    while True:
        command = input("Enter command (START/STOP/EXIT): ").strip().upper()

        if command == "START":
            if not main.is_running.is_set():
                print("Starting acquisition...")
                main.reader_wifi.conn.sendall(b"START\n")
                main.start_acquisition()
                    

        elif command == "STOP":
            if main.is_running.is_set():
                print("Stopping acquisition...")
                main.stop_acquisition()
                main.reader_wifi.conn.sendall(b"STOP\n")
                time.sleep(2)
                break