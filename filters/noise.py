import numpy as np
import numpy.typing as npt
from typing import List
from filters.filter_base import Filter

class Noise(Filter):
    name = "Noise"
    description = "A filter to insert noise into the CSI data."
    author = "Author Name"
    version = "1.0.0"

    def __init__(self):
        super().__init__()
        self.add_config("mean", 0.0, -20, 20)
        self.add_config("std", 10.0, 0, 100)

    def apply(self, amp: npt.NDArray[np.float32], phase: npt.NDArray[np.float32], ts: List[float]):
        amp[-1] += np.random.normal(self.get("mean"), self.get("std"), size=amp[-1].shape)
