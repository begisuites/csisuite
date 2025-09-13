import numpy as np
import pyqtgraph as pg
from services.api import Api
from plugins.plugin_base import Plugin
from utils.visualization import *

class SuddenChanges(Plugin):
    name = "Sudden Changes"
    description = "A plugin to visualize sudden changes in the data."
    author = "Bellizi, Gili"
    version = "1.0.0"

    def __init__(self, api : Api):
        super().__init__(api)
        win = pg.GraphicsLayoutWidget()
        sudden_changes_plot = win.addPlot(title="Sudden Changes", axisItems={'bottom': MinuteSecondAxis(orientation='bottom')})
        sudden_changes_plot.setLabels(bottom='Time', left='Subcarrier')
        self.sudden_changes = pg.ImageItem()
        self.sudden_changes.setLookupTable(pg.colormap.get('viridis', source='matplotlib').getLookupTable(0, 1, 256))
        sudden_changes_plot.addItem(self.sudden_changes)
        api.ui().add_dock("Sudden Changes", win, size=(2, 1), position='above', relativeTo="Spectrogram Diff")
        api.ui().add_plot("Sudden Changes", sudden_changes_plot)

    def deactivate(self):
        self.api.ui().remove_plot("Sudden Changes")
        self.api.ui().remove_dock("Sudden Changes")

    def build(self):
        spectrogram = self.api.ui().get_plot("Spectrogram")
        sudden_changes_plot = self.api.ui().get_plot("Sudden Changes")
        sudden_changes_plot.setXLink(spectrogram)
        sudden_changes_plot.setYLink(spectrogram)

    def render(self, tick):
        if not self.api.ui().is_dock_visible("Sudden Changes"):
            return
        
        amp = self.api.csi().get_amp()
        ts = self.api.csi().get_ts()

        sudden_changes = np.abs(np.diff(amp, n=2, axis=0))
        self.sudden_changes.setImage(sudden_changes, autoLevels=len(sudden_changes) > 0)
        self.sudden_changes.setRect(pg.QtCore.QRectF(ts[0], 0, ts[-1] - ts[0], amp.shape[1])) if amp.size > 0 else None

    def render_schedule(self) -> int:
        return 1