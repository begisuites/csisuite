import numpy as np
import pyqtgraph as pg
from plugins.plugin_base import Plugin
from utils.visualization import *

class EnergyDistribution(Plugin):
    name = "Energy Distribution"
    description = "A plugin to visualize the energy distribution of the data."
    author = "Bellizzi, Gili"
    version = "1.0.0"

    def __init__(self, api):
        super().__init__(api)
        win = pg.GraphicsLayoutWidget()
        energy_plot = win.addPlot(title="Energy Distribution")
        energy_plot.setLabels(bottom='Subcarrier', left='Energy (dB)')
        self.energy_curve = energy_plot.plot(pen='w')
        api.ui().add_dock("Energy Distribution", win, size=(2, 1), position='above', relativeTo="Spectrogram Diff")
        api.ui().add_plot("Energy Distribution", energy_plot)
        
    def deactivate(self):
        self.api.ui().remove_plot("Energy Distribution")
        self.api.ui().remove_dock("Energy Distribution")
        
    def render(self, tick):
        if not self.api.ui().is_dock_visible("Energy Distribution"):
            return

        amp = self.api.csi().get_amp()
        mask = self.api.csi().get_mask()

        energy_per_subcarrier = np.sum(amp**2, axis=0)
        total_energy = np.sum(energy_per_subcarrier)
        energy_distribution = energy_per_subcarrier / total_energy if total_energy > 0 else energy_per_subcarrier
        self.energy_curve.setData(np.arange(-128, 128)[mask], energy_distribution if amp.size > 0 else [])

    def render_schedule(self) -> int:
        """Return the number of render rounds to wait before the next render call."""
        return 1