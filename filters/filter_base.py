import numpy as np
import numpy.typing as npt
from typing import List
from utils.configurable import Configurable

class Filter(Configurable):
    name = "Filter Name"
    description = "A description of the filter."
    author = "Author Name"
    version = "1.0.0"

    def __init__(self):
        super().__init__()
        self.enabled = False
        self.perf_ticks : np.ndarray = np.zeros(100)

    def is_enabled(self) -> bool:
        return self.enabled
    
    def set_enabled(self, enabled: bool):
        self.enabled = enabled

    def apply(self, amp: npt.NDArray[np.float32], phase: npt.NDArray[np.float32], ts: List[float]):
        pass

    def add_performance_time(self, time: float):
        """
        Add a performance tick to the filter's performance tracking.
        This method is called to record the time taken for each filter call.
        """
        self.perf_ticks = np.roll(self.perf_ticks, -1)
        self.perf_ticks[-1] = time