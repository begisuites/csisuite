import numpy as np

class Configurable():
    def __init__(self, **kwargs):
        self._config = kwargs
        self._constraints = {}

    def get(self, key, default=None):
        return self._config.get(key, default)

    def set(self, key, value):
        min_val, max_val = self._constraints[key]
        old_value = self._config.get(key)
        self._config[key] = np.clip(value, min_val, max_val)
        self.on_config_change(key, old_value, value)

    def get_config(self):
        return self._config.items()

    def get_config_constraints(self):
        return self._constraints

    def add_config(self, key, value, min_val=None, max_val=None):
        self._config[key] = value
        self._constraints[key] = (min_val, max_val)

    def on_config_change(self, key, old_value, new_value):
        print(f"⚙️  Config '{key}' changed from {old_value} to {new_value}")