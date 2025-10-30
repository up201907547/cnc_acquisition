import pdfplumber
import pandas as pd
import re
import json
import logging
def extract_CAM_info_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        all_text = []

        for page in pdf.pages:
            text = page.extract_text()
            if text:
                all_text.append(text)

        text = "\n".join(all_text)

    CAM_dict = {}

    words = text.split()
    timers = []

    for word in words:
        if re.match(r"\b\d{2}:\d{2}:\d{2}\b", word):
            timers.append(word)

    print(len(timers))

    for i in range(len(timers)):
        CAM_dict[f'Op_{i+1}'] = timers[i]

    print(CAM_dict)

    with open(r"C:\Users\Lenovo\Desktop\CNC_Influx2\config\CAM_info.json", "w") as f:
        json.dump(CAM_dict, f, indent=4)
    return

class JsonLogger(logging.Formatter):
    def format(self, record):
        log_record = {'message': record.getMessage()}
        return json.dumps(log_record)
    
formatter = logging.Formatter('%(asctime)s - %(message)s')

class TextLogger(logging.Formatter):
    def format(self, record):
        return f"{record.getMessage()}"