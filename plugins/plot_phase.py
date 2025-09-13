import numpy as np
import pyqtgraph as pg
from services.api import Api
from pyqtgraph.Qt import QtCore, QtWidgets
from plugins.plugin_base import Plugin

class PlotPhasePlugin(Plugin):
    name = "Phase"
    description = "A plugin to visualize phase information of the data."
    author = "Bellizi, Gili"
    version = "1.0.0"
    
    def __init__(self, api: Api):
        super().__init__(api)
        self.phase_unwrap = True    # Whether to unwrap phase values
    
        win = pg.GraphicsLayoutWidget()
        self.plot_widget = win.addPlot(title="Phase")
        self.plot_widget.setLabels(left='Phase', bottom='Subcarrier')
        self.plot_widget.setYRange(-200, 200, padding=0.1)
        
        pen = pg.mkPen(color='r', width=2)
        curve = self.plot_widget.plot([], [], pen=pen, name='Phase')
        self.phase_curves = [curve]

        api.ui().add_dock('Phase', win, size=(2, 1), position='below', relativeTo="Spectrogram")
        self.api.ui().add_plot("Phase", self.plot_widget)

    def deactivate(self):
        self.api.ui().remove_plot("Phase")
        self.api.ui().remove_dock("Phase")

    def render(self, tick):
        if not self.api.ui().is_dock_visible("Phase"):
            return
        
        try:
            mask = self.api.csi().subcarrier_mask
            phase = self.api.csi().get_phase()
            phase = np.unwrap(phase, axis=0)
            phase = phase[-1] if phase.size > 0 else phase
            self.phase_curves[0].setData(np.arange(-128, 128)[mask], phase)

        except Exception as e:
            print(f"Error updating phase plot: {e}")

    def render_schedule(self) -> int:
        return 1