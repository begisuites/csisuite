import time
import threading
import numpy as np
from services.api import Api
from readers.reader_base import Reader
from utils.preprocess import to_db

class ReaderThread(threading.Thread):
    def __init__(self, api: Api, reader: Reader, window=2048):
        super(ReaderThread, self).__init__()
        self.window = window
        self.reader = reader
        self.api = api

    def run(self):
        print(f"Starting {self.reader.get_name()}...")
        start_time = None
        for count, (ts, csi, mac) in enumerate(self.reader):
            if start_time is None:
                start_time = time.time()
            self.api.csi().push(mac, csi, ts)
            if count % 500 == 0:
                elapsed = time.time() - start_time
                print(f"[{ts.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] Received {count} frames in {elapsed:.2f} seconds")