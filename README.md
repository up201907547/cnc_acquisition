# Sensor Monitoring Application

This is a sensor monitoring application designed to interface with a NI Data Acquisition (DAQ) system and display real-time measurements from various sensors such as current, vibration, and force sensors.

## 📋 Overview

The application allows users to monitor data from multiple sensor channels defined in a configuration file. It provides a graphical user interface (GUI) for configuring sensor types and sampling rates, and it relies on an InfluxDB server to store and access measurement data and in Grafana to plot Live measurements.

## ⚙️ Configuration

Before running the application, make sure: 

Setup the DAQ channel mapping:
    The configuration file is located at: .\config\daq_ch_map.json
    -Please dont remove subsections of the dictionary, change or add channels in each subsection

Setup the Aquisition parameters:
    This configuration is located on GUI.py program in Main class __init__.
    You can define:
        -sampling rate
        -Sensor types used: "Current" or "Vibration" or "Force", or all at same time.
        -Dont change the boleans

Setup Influx Server:
    Open Windows powershell:
        - Go to Influx data folder: cd "C:\Program Files\InfluxData"
        - Run: .\influxd

Now you are ready to start the GUI.py program.

