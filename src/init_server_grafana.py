import subprocess
#import webbrowser
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

class InitServer:
    def __init__(self):
        # Command to start the InfluxDB server
        #command = [r"C:\Program Files\InfluxData\influxd"]
        #self.process = subprocess.Popen(command)
        
        url = "http://localhost:3000/d/dekzlbqzejp4we/daq?orgId=1&from=now-10s&to=now&timezone=browser&refresh=auto"
        
        #webbrowser.open(url)

        # Start Grafana in a Selenium-controlled browser
        chrome_options = Options()
        chrome_options.add_experimental_option("detach", False)  # We'll manage closing it
        self.browser = webdriver.Chrome(options=chrome_options)
        self.browser.get(url)
        self.browser.maximize_window()

    def stop(self):
        self.browser.quit()

    def close(self):
        # Stop the InfluxDB server
        #self.process.terminate()
        #self.process.wait()
        self.stop()

    # Example usage:
if __name__ == "__main__":
    server = InitServer()
    try:
        time.sleep(20)  # Let the server run for 10 seconds
    finally:
        server.close()
