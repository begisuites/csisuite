import threading
import numpy as np
from typing import Dict, List, TypedDict, TypeAlias
import numpy.typing as npt
from utils.preprocess import to_db
from services.filters import Filters

Mac: TypeAlias = str

class CSIEntry(TypedDict):
    raw: npt.NDArray[np.complex64]     # e.g., shape (N, S)
    amp: npt.NDArray[np.float32]       # e.g., shape (N, S)
    phase: npt.NDArray[np.float32]     # e.g., shape (N, S)
    ts: List[float]                    # timestamps aligned with rows in arrays

class CSI:
    def __init__(self, subcarrier_mask=None, window=2048):
        self.csi_data : Dict[Mac, CSIEntry] = {}
        self.mutex = threading.Lock()
        self.selected_mac = None
        self.set_mask(subcarrier_mask)
        self.reader = None
        self.window = window
        self.filters : Filters = Filters()

    def get_macs(self):
        with self.mutex:
            return list(self.csi_data.keys())

    def get_amp(self):
        if self.selected_mac:
            return self.csi_data[self.selected_mac]['amp']
        return np.empty((0, self.subcarrier_num))

    def get_phase(self):
        if self.selected_mac:
            return self.csi_data[self.selected_mac]['phase']
        return np.empty((0, self.subcarrier_num))

    def get_ts(self):
        return self.csi_data[self.selected_mac]['ts'] if self.selected_mac else []

    def get_mask(self):
        return self.subcarrier_mask

    def set_mask(self, mask):
        with self.mutex:
            self.subcarrier_mask = np.ones(256, dtype=bool) if mask is None else mask
            self.subcarrier_num = np.sum(self.subcarrier_mask)
            self.csi_data = {}  # Clear existing data as it may not match new mask
            print(f"CSI mask set. Number of subcarriers: {self.subcarrier_num}")

    def set_reader(self, reader):
        self.reader = reader

    def set_selected_mac(self, mac):
        with self.mutex:
            if mac in self.csi_data:
                self.selected_mac = mac

    def clear(self):
        self.csi_data = {}
        self.selected_mac = None
        self.reader.receiver.clear()
    
    def push(self, mac, csi, ts):
        with self.mutex:
            if mac not in self.csi_data:
                self.csi_data[mac] = { 
                    'raw': np.empty((0, self.subcarrier_num)), 
                    'amp': np.empty((0, self.subcarrier_num)),
                    'phase': np.empty((0, self.subcarrier_num)),
                    'ts': [] 
                }

            # Control check to ensure CSI array length matches the subcarrier_mask
            if csi.shape[0] != self.subcarrier_mask.shape[0]:
                print(f"Skipping frame: mismatched shape {csi.shape[0]} vs {self.subcarrier_mask.shape[0]}")
                return

            raw = csi[self.subcarrier_mask].reshape(1, -1)
            amp = to_db(raw)
            phase = np.angle(raw)

            self.csi_data[mac]['raw'] = np.vstack((self.csi_data[mac]['raw'], raw))[-self.window:]
            self.csi_data[mac]['amp'] = np.vstack((self.csi_data[mac]['amp'], amp))[-self.window:]
            self.csi_data[mac]['phase'] = np.vstack((self.csi_data[mac]['phase'], phase))[-self.window:]
            self.csi_data[mac]['ts'].append(ts.timestamp())
            self.csi_data[mac]['ts'] = self.csi_data[mac]['ts'][-self.window:]

            self.filters.apply_filters(self.csi_data[mac]['amp'], self.csi_data[mac]['phase'], self.csi_data[mac]['ts'])