class State:
    def __init__(self):
        self._state = {}

    def set(self, key, value):
        """Set a value in the state."""
        self._state[key] = value

    def get(self, key):
        """Get a value from the state."""
        val = self._state.get(key)
        return val() if callable(val) else val

    def remove(self, key):
        """Remove a value from the state."""
        if key in self._state:
            del self._state[key]

    def clear(self):
        """Clear the entire state."""
        self._state.clear()

    def all(self):
        """Get all state values."""
        return self._state.copy()