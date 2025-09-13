import numpy as np
from services.api import Api
from utils.configurable import Configurable

class Plugin(Configurable):
    name = "Plugin Name"
    description = "A description of the plugin."
    author = "Author Name"
    version = "1.0.0"
    is_manageable = True

    def __init__(self, api: Api):
        """
        Activate the plugin. Instantiate plugin components here.
        This method is called when the plugin is loaded by the API, and it should be used to set up any necessary resources.
        """
        self.api = api
        self.perf_ticks : np.ndarray = np.zeros(100)
    
    def deactivate(self):
        """
        Cleanup resources when the plugin is unloaded.
        This method is called when the plugin is unloaded or the application is closed.
        It should be used to release any resources that were allocated during the plugin's lifetime, and it should return True if the plugin was successfully unloaded.
        Unloading implementation is required to enable hot reloading of plugins.
        """
        pass

    def build(self):
        """
        Build the plugin's UI components. 
        This method is called after all plugins have been initialized, so it can be used to finalize the UI setup.
        """
        pass

    def render(self, tick):
        """
        This method is called periodically to update the plugin's visual representation."""
        pass
    
    def render_schedule(self) -> int:
        """
        Return the number of render rounds to wait before the next render call.
        This is used to control how often the plugin's render method is called.
        """
        return float('inf')
    
    def supports_hot_reload(self) -> bool:
        """
        Return True if the plugin supports hot reloading.
        If True, the plugin will be reloaded when the code is changed.
        It is mandatory to implement deactivate() method to support hot reloading.
        """
        return False

    def add_performance_time(self, time: float):
        """
        Add a performance tick to the plugin's performance tracking.
        This method is called to record the time taken for each render call.
        """
        self.perf_ticks = np.roll(self.perf_ticks, -1)
        self.perf_ticks[-1] = time