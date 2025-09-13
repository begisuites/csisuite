import numpy as np
import pyqtgraph as pg
from services.api import Api
from pyqtgraph.Qt import QtCore, QtWidgets
from plugins.plugin_base import Plugin

class SNRPlugin(Plugin):
    name = "SNR"
    description = "Bar chart of per-subcarrier Signal-to-Noise Ratio (dB)."
    author = "Bellizi, Gili"
    version = "1.0.0"

    def __init__(self, api: Api, window_size: int = 256, eps: float = 1e-12):
        super().__init__(api)
        self.window_size = window_size
        self.eps = eps

        win = pg.GraphicsLayoutWidget()
        self.plot_widget = win.addPlot(title="Signal-to-Noise Ratio (SNR) per Subcarrier (dB)")
        self.plot_widget.setLabels(left='SNR (dB)', bottom='Subcarrier')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.25)

        self.bar_item = pg.BarGraphItem(x=[], height=[], width=1.0, brush=pg.mkBrush(100, 150, 255))
        self.plot_widget.addItem(self.bar_item)

        api.ui().add_dock('SNR', win, size=(2, 1), position='below', relativeTo="Spectrogram")
        api.ui().add_plot("SNR", self.plot_widget)

    def deactivate(self):
        self.api.ui().remove_plot("SNR")
        self.api.ui().remove_dock("SNR")

    def render(self, tick):
        if not self.api.ui().is_dock_visible("SNR"):
            return

        amp = self.api.csi().get_amp()

        if len(amp) < self.window_size:
            self.bar_item.setOpts(x=[], height=[], brushes=[])
            return
        
        mu = np.mean(amp, axis=0)
        sigma = np.std(amp, axis=0)
        snrs = mu / (sigma + 1e-9)

        # TODO: this threshold should be configurable
        # Low variance corresponds to null subcarriers 
        variance = np.var(amp, axis=0)
        snrs = np.where(variance < 2, 0.1, snrs)

        mask = self.api.csi().get_mask()
        x = np.arange(-128, 128)[mask]

        # TODO: this threshold should be configurable
        # threshold is 10% of max SNR
        threshold = 0.15 * np.max(snrs)
        colors = np.where(snrs < threshold, pg.mkBrush(255, 100, 100), pg.mkBrush(100, 150, 255))

        self.bar_item.setOpts(x=x, height=snrs, brushes=colors)

        # Y range auto with some padding
        ymin = float(np.min(snrs))
        ymax = float(np.max(snrs))
        pad = max(1.0, 0.05 * (ymax - ymin + 1e-6))
        self.plot_widget.setYRange(ymin - pad, ymax + pad, padding=0)

    def render_schedule(self) -> int:
        return 1