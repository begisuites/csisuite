import pathlib
from typing import TYPE_CHECKING
from pyqtgraph.Qt import QtWidgets
from services.settings import Settings
from services.models import Models
from services.state import State
from services.csi import CSI
from services.ui import UI
from services.style import Style
from PySide6.QtCore import Signal, QObject
from PySide6.QtWidgets import QApplication

if TYPE_CHECKING:   # Only for type hints, no runtime import
    from app.services.plugins import PluginManager

class Api(QObject):
    on_record_start = Signal()
    on_record_stop = Signal(str)
    on_replay_start = Signal(str)

    def __init__(self, app: QApplication, main_window: QtWidgets.QMainWindow):
        super().__init__()
        self._main_window = main_window
        self._ui = UI(main_window)
        self._styles = Style(app, project_root=pathlib.Path(__file__).parent.parent, dev_watch=True)
        self._csi = CSI()
        self._state = State()
        self._models = Models(num_classes=5)
        self._settings = Settings()
        self._plugins = None

    def window(self) -> QtWidgets.QMainWindow:
        return self._main_window
    
    def ui(self) -> UI:
        return self._ui

    def styles(self) -> Style:
        return self._styles
    
    def csi(self) -> CSI:
        return self._csi
    
    def state(self) -> State:
        return self._state

    def models(self) -> Models:
        return self._models
    
    def settings(self) -> Settings:
        return self._settings

    def plugins(self) -> 'PluginManager':
        return self._plugins

    def set_plugins(self, plugins: 'PluginManager'):
        self._plugins = plugins