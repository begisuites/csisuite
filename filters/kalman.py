import numpy as np
import numpy.typing as npt
from typing import List
from filters.filter_base import Filter

class AdaptiveKalman:
    def __init__(self, q=1.0, r=1.0, alpha=0.05, dim_x=256):
        self.alpha = alpha
        self.q = q
        self.r = np.ones(dim_x) * r

        self.x = None
        self.P = np.ones(dim_x)
        self.prev_x = None

    def update(self, z):
        # Initialization
        if self.x is None:
            self.x = z

        # Prediction
        x_pred = self.x
        P_pred = self.P + self.q

        residual = z - x_pred
        K = P_pred / (P_pred + self.r + 1e-10)   # Avoid division by zero

        # Update
        self.x = x_pred + K * residual
        self.P = (1 - K) * P_pred

        # Adaptive variance update
        if self.prev_x is not None:
            dx = self.x - self.prev_x
            self.q = (1 - self.alpha) * self.q + self.alpha * dx**2
            self.r = (1 - self.alpha) * self.r + self.alpha * residual**2

        self.prev_x = self.x
        return self.x

class KalmanFilter(Filter):
    name = "Adaptive Kalman"
    description = "An Adaptive Kalman filter implementation."
    author = "Bellizzi, Gili"
    version = "1.0.0"

    def __init__(self):
        super().__init__()
        self.add_config("alpha", 0.5, 0.0, 1.0)
        self.kalman_filter = AdaptiveKalman(alpha=self.get("alpha"), dim_x=256)

    def apply(self, amp: npt.NDArray[np.float32], phase: npt.NDArray[np.float32], ts: List[float]):
        if amp.shape[1] != self.kalman_filter.P.shape[0]:
            self.kalman_filter = AdaptiveKalman(alpha=self.get("alpha"), dim_x=amp.shape[1])

        self.kalman_filter.alpha = self.get("alpha")
        self.kalman_filter.update(amp[-1])
        amp[-1] = self.kalman_filter.x
