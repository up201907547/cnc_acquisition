import subprocess
#import webbrowser
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException


class InitServer:
    def __init__(self, url=None):
        self.url = url or (
            "http://localhost:3000/d/dekzlbqzejp4we/daq?"
            "orgId=1&from=now-10s&to=now&timezone=browser&refresh=auto"
        )

        self.browser = None

        try:
            self.start_browser()
        except WebDriverException as e:
            print(f"Failed to start browser: {e}")
    
    def start_browser(self):
        chrome_options = Options()
        chrome_options.add_argument("--start-fullscreen")
        chrome_options.add_experimental_option("detach", False)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

        self.browser = webdriver.Chrome(options=chrome_options)
        self.browser.get(self.url)

    def stop(self):
        if self.browser:
            self.browser.quit()

    def close(self):
        self.stop()

    # Example usage:
if __name__ == "__main__":
    server = InitServer()
    try:
        time.sleep(10)  # Let the server run for 10 seconds
    finally:
        server.close()
