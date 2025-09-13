import numpy as np
import pyqtgraph as pg
from services.api import Api
from plugins.plugin_base import Plugin
from utils.visualization import *

class Spectrogram(Plugin):
    name = "Spectrogram"
    description = "A plugin to visualize spectrograms of the data."
    author = "Bellizi, Gili"
    version = "1.0.0"
    is_manageable = False

    def __init__(self, api: Api):
        super().__init__(api)
        self.add_spectrogram(api)
        self.add_subcarriers_amplitude(api)
        self.add_subcarrier_sample(api)

    def deactivate(self):
        self.api.ui().remove_plot("Spectrogram")
        self.api.ui().remove_dock("Spectrogram")
        self.api.ui().remove_plot("Amplitude")
        self.api.ui().remove_dock("Amplitude")
        self.api.ui().remove_plot("Subcarriers Sample")
        self.api.ui().remove_dock("Subcarriers Sample")

    def add_spectrogram(self, api: Api):
        win = pg.GraphicsLayoutWidget()
        p1 = win.addPlot(title="CSI Spectrogram", axisItems={'bottom': MinuteSecondAxis(orientation='bottom')})
        p1.setLabels(bottom='Time', left='Subcarrier')
        self.spect = pg.ImageItem()
        self.spect.setLookupTable(pg.colormap.get('jet', source='matplotlib').getLookupTable(0, 1, 256))
        p1.addItem(self.spect)
        api.ui().add_dock("Spectrogram", win, size=(2, 1), position='top')
        api.ui().add_plot("Spectrogram", p1)

    def add_subcarriers_amplitude(self, api: Api):
        win = pg.GraphicsLayoutWidget()
        p2 = win.addPlot(title="Subcarrier Amplitude")
        p2.setLabels(bottom='Subcarrier', left='Amplitude (dB)')
        p2.setMouseEnabled(x=False, y=False)
        self.last_amp = p2.plot(pen='y')
        p2.setYRange(0, 100, padding=0.1)
        
        # Interactive subcarrier selector lines
        self.lines = []
        for color, freq in zip(['r', 'g', 'c'], [-53, -25, 0]):
            line = pg.InfiniteLine(pos=freq, angle=90, movable=True, pen=color)
            p2.addItem(line)
            self.lines.append(line)

        # Interactive spectrogram limits 
        self.limit_min = pg.InfiniteLine(pos=30, angle=0, movable=True, pen='w', label='Min Limit', labelOpts={'position': 0.1})
        self.limit_max = pg.InfiniteLine(pos=80, angle=0, movable=True, pen='w', label='Max Limit', labelOpts={'position': 0.1})
        p2.addItem(self.limit_min)
        p2.addItem(self.limit_max)
        api.ui().add_dock("Amplitude", win, size=(1, 1), position='right', relativeTo="Spectrogram")
        api.ui().add_plot("Amplitude", p2)

    def add_subcarrier_sample(self, api: Api):
        win = pg.GraphicsLayoutWidget()
        self.p4 = win.addPlot(title="Subcarriers Sample")
        self.p4.setLabels(bottom='Frame Index', left='Amplitude (dB)')
        self.p4.addLegend()
        self.history_curves = [self.p4.plot(name='Subcarrier', pen=color) for color in ['r', 'g', 'c']]
        api.ui().add_dock("Subcarriers Sample", win, size=(1, 1), position='bottom', relativeTo="Amplitude")
        api.ui().add_plot("Subcarriers Sample", self.p4)

    def build(self):
        self.api.ui().get_dock("Spectrogram").raiseDock()
        self.api.ui().get_dock("Amplitude").raiseDock()

    def render(self, tick):
        amp = self.api.csi().get_amp()
        ts = self.api.csi().get_ts()
        
        # Spectrogram
        self.spect.setImage(amp, levels=(self.limit_min.value(), self.limit_max.value()))
        self.spect.setRect(pg.QtCore.QRectF(ts[0], 0, ts[-1] - ts[0], amp.shape[1])) if amp.size > 0 else None

        # Last CSI amplitude
        self.last_amp.setData(np.arange(-128, 128)[self.api.csi().get_mask()], amp[-1] if amp.size > 0 else [])

        # Subcarriers sample
        selected_indices, selected_freqs = self.get_selected_subcarriers()
        for i, pos in enumerate(selected_indices):
            history = amp[:, pos]
            self.history_curves[i].setData(history)
            self.p4.legend.items[i][1].setText(f"Subcarrier {selected_freqs[i]}")

    def render_schedule(self) -> int:
        return 1
    
    def get_selected_subcarriers(self):
        x_positions = [int(round(line.value())) for line in self.lines]
        valid_freqs = np.arange(-128, 128)[self.api.csi().get_mask()]
        selected_indices = [np.argmin(np.abs(valid_freqs - x)) for x in x_positions]
        return selected_indices, x_positions