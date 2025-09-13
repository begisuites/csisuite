import os
import pathlib
from pyqtgraph.Qt import QtCore, QtWidgets
from utils.configurable import Configurable
from services.plugins import PluginManager
from services.api import Api
from utils.preprocess import *
from PySide6.QtWidgets import QApplication
from readers.reader_thread import ReaderThread
from readers.nexmon import NexmonCSIStreamReader    

PLUGIN_DIR = pathlib.Path(__file__).parent / "plugins"
MODELS_DIR = pathlib.Path(__file__).parent / "models"
FILTERS_DIR = pathlib.Path(__file__).parent / "filters"

class Application(QtWidgets.QMainWindow):
    def __init__(self, app: QApplication):
        super().__init__()
        self.closeEvent = lambda e: (os._exit(0), e.accept())
        self.setWindowTitle("Live Nexmon-CSI Stream Viewer")

        self.api = Api(app, self)
        self.api.styles().add_file("core", "main", "style.qss", priority=0)
        # self.api.csi().set_mask(get_used_subcarriers())

        reader = NexmonCSIStreamReader('0.0.0.0', 9000)
        self.api.csi().set_reader(reader)

        reader_thread = ReaderThread(self.api, reader)
        reader_thread.start()

        self.api.set_plugins(PluginManager(self.api, PLUGIN_DIR))
        self.api.csi().filters.load_filters(FILTERS_DIR)
        self.api.plugins().load_plugins()
        self.api.plugins().start_hot_reload()
        self.api.models().load_models(self.api, MODELS_DIR)
        self.api.ui().build()
        self.api.plugins().build()

        self.timer_render = QtCore.QTimer()
        self.timer_prediction = QtCore.QTimer()

        self.setup_prediction_settings()

    def start(self):
        # Update plots every 30 ms
        self.render_tick = 0
        self.timer_render = QtCore.QTimer()
        self.timer_render.timeout.connect(self.api.plugins().render)
        self.timer_render.start(30)

        # Update predictions every 500 ms
        self.timer_prediction.timeout.connect(self.update_predictions)
        self.timer_prediction.start(500)

    def update_predictions(self):
        self.api.models().update_predictions(self.api.csi())

    def setup_prediction_settings(self):
        prediction_settings = Configurable()
        prediction_settings.add_config("interval_ms", 500, 250, 10000)
        prediction_settings.add_config("consensus_window", 1, 1, 100)
        prediction_settings.add_config("min_confidence", 0.1, 0.0, 1.0)

        def on_change(key, old_value, new_value):
            if key == "interval_ms":
                self.timer_prediction.setInterval(new_value)

        prediction_settings.on_config_change = on_change
        self.api.settings().add("Predictions", prediction_settings)
