from typing import Dict
from utils.configurable import Configurable

class Settings():
    def __init__(self):
        self._settings : Dict[str, Configurable] = {}

    def get(self, section, key, default=None):
        if not section in self._settings:
            return default
        
        return self._settings[section].get(key, default)

    def add(self, name: str, setting: Configurable):
        if name in self._settings:
            raise ValueError(f"Setting '{name}' already exists.")
        self._settings[name] = setting

    def get_all(self):
        return self._settings
