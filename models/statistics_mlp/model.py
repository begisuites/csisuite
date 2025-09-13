import numpy as np
from models.model_base import HARModel
from services.api import Api
from scipy.special import softmax

# TODO: Replace with actual model
class StatisticalMLP(HARModel):
    def __init__(self, api: Api, num_classes: int):
        super().__init__(num_classes)
        self.api = api

    def evaluate(self, amp, ts) -> tuple[float, np.ndarray]:
        ts_to = ts[-1]
        ts_from_idx = np.searchsorted(np.array(ts), ts_to - 3.0)
        return ts[ts_from_idx], ts_to, softmax(np.random.rand(self.num_classes))
