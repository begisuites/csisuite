import numpy as np

class HARModel():
    def __init__(self, num_classes: int):
        self.num_classes = num_classes

    def get_name(self) -> str:
        """
        Get the name of the model.
        """
        return self.__class__.__name__

    def evaluate(self, amp, ts) -> tuple[float, float, np.ndarray]:
        """
        Evaluate the model with the given amplitude and timestamp data.
        This method should be overridden by subclasses to implement specific model logic.
        Returns a tuple containing the Unix timestamp and a numpy array of shape (num_classes) with confidence scores.
        """
        raise NotImplementedError("Subclasses must implement this method.")
