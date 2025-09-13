import numpy as np
import pyqtgraph as pg
from services.api import Api
from plugins.plugin_base import Plugin
from utils.visualization import *

class SpectrogramDiff(Plugin):
    name = "Spectrogram Diff"
    description = "A plugin to visualize the difference of spectrograms."
    author = "Bellizzi, Gili"
    version = "1.0.0"

    def __init__(self, api: Api):
        super().__init__(api)
        win = pg.GraphicsLayoutWidget()
        p3 = win.addPlot(title="CSI Spectrogram Diff", axisItems={'bottom': MinuteSecondAxis(orientation='bottom')})
        p3.setLabels(bottom='Time', left='Subcarrier')
        self.spect_diff = pg.ImageItem()
        self.spect_diff.setLookupTable(pg.colormap.get('viridis', source='matplotlib').getLookupTable(0, 1, 256))
        p3.addItem(self.spect_diff)
        api.ui().add_dock("Spectrogram Diff", win, size=(2, 1), position='bottom', relativeTo="Spectrogram")
        api.ui().add_plot("Spectrogram Diff", p3)

    def deactivate(self):
        self.api.ui().remove_plot("Spectrogram Diff")
        self.api.ui().remove_dock("Spectrogram Diff")

    def build(self):
        spectrogram = self.api.ui().get_plot("Spectrogram")
        spectrogram_diff = self.api.ui().get_plot("Spectrogram Diff")
        spectrogram_diff.setXLink(spectrogram)
        spectrogram_diff.setYLink(spectrogram)
        
    def render(self, tick):
        if not self.api.ui().is_dock_visible("Spectrogram Diff"):
            return
        
        amp = self.api.csi().get_amp()
        ts = self.api.csi().get_ts()
        
        amp_diff = np.abs(np.diff(amp, axis=0))
        
        self.spect_diff.setImage(amp_diff, autoLevels=False)
        self.spect_diff.setRect(pg.QtCore.QRectF(ts[0], 0, ts[-1] - ts[0], amp.shape[1]-1)) if amp_diff.size > 0 else None

        # Spectrogram levels
        if amp_diff.size > 0 and tick % 100 == 0:
            self.spect_diff.setLevels((np.percentile(amp_diff, 10), np.percentile(amp_diff, 95)))

    def render_schedule(self) -> int:
        return 1