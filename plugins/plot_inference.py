import numpy as np
import pyqtgraph as pg
from services.api import Api
from plugins.plugin_base import Plugin
from utils.visualization import *

class Inference(Plugin):
    name = "Inference"
    description = "A plugin to visualize predictions in the data."
    author = "Bellizi, Gili"
    version = "1.0.0"

    def __init__(self, api : Api):
        super().__init__(api)
        win = pg.GraphicsLayoutWidget()
        self.inference_plot = win.addPlot(title="Inference", axisItems={'bottom': MinuteSecondAxis(orientation='bottom')})
        self.inference_plot.setLabels(bottom='Time', left='Activity')
        self.inference_plot.setYRange(0, len(api.models().get_classes()), padding=0.1)
        self.inference_plot.getAxis('left').setTicks([[(i, activity) for i, activity in enumerate(api.models().get_classes())]])
        self.inference_plot.setMouseEnabled(x=True, y=False)
        self.inference = pg.ScatterPlotItem(size=10, pen=None, brush='b', hoverable=True)
        self.inference_plot.addItem(self.inference)
        self.inference_plot.showGrid(x=False, y=True, alpha=0.8)
        self.inference.sigHovered.connect(self.on_prediction_hovered)
        
        self.highlight_from = None
        self.highlight_to = None

        self.spect_highlight = pg.ImageItem()
        self.spect_highlight.setOpacity(0.5)
        self.spect_highlight.setVisible(False)

        api.ui().add_dock("Inference", win, size=(2, 1), position='above', relativeTo="Spectrogram Diff")
        api.ui().add_plot("Inference", self.inference_plot)

    def deactivate(self):
        self.api.ui().remove_plot("Inference")
        self.api.ui().remove_dock("Inference")

    def build(self):
        spect = self.api.ui().get_plot("Spectrogram")
        spect.addItem(self.spect_highlight)

    def on_prediction_hovered(self, plot, points):
        self.spect_highlight.setVisible(points.size != 0)
        self.highlight_from = points[0].data() if points.size > 0 else None
        self.highlight_to = points[0].pos().x() if points.size > 0 else None

    def render(self, tick):
        ts = self.api.csi().get_ts()
        self.inference_plot.getViewBox().setXRange(ts[0], ts[-1], padding=0) if ts else None
        predictions = self.api.models().get_predictions()
        
        if predictions:
            predictions = self.apply_consensus(predictions)

            ts_from, ts_to, probs = zip(*predictions)
            confidences = [np.max(conf) for conf in probs]
            classes = [np.argmax(conf) for conf in probs]
            sizes = [5 + 20 * conf for conf in confidences]
            
            class_colors = {
                'walk': (255, 0, 0),      # Red
                'quiet': (0, 255, 0),    # Green
                'sit_down': (0, 0, 255), # Blue
                'stand_up': (255, 255, 0), # Yellow
                'fall': (255, 0, 255)    # Magenta
            }

            brushes = [pg.mkBrush(*class_colors[self.api.models().get_classes()[cls]]) for cls in classes]
            self.inference.setData(x=ts_to, y=classes, data=ts_from, symbol='o', size=sizes, brush=brushes)
        else:
            self.inference.setData(x=[], y=[])

        if self.highlight_from is not None and self.highlight_to is not None:
            amp = self.api.csi().get_amp()
            highlight = np.zeros_like(amp)
            pos_x_from = np.searchsorted(ts, self.highlight_from)
            pos_x_to = np.searchsorted(ts, self.highlight_to)
            highlight[pos_x_from:pos_x_to, :] = 1
            self.spect_highlight.setImage(highlight)
            self.spect_highlight.setRect(pg.QtCore.QRectF(ts[0], 0, ts[-1] - ts[0], amp.shape[1]))

    def apply_consensus(self, predictions):
        consensus_window = self.api.settings().get("Predictions", "consensus_window", 1)
        min_confidence = self.api.settings().get("Predictions", "min_confidence", 0.0)

        if consensus_window <= 1 and min_confidence <= 0.0:
            return predictions

        result, run, prev = [], 0, None
        for p in predictions:
            cls = np.argmax(p[2])  # (ts_from, ts_to, probs)
            confidence = np.max(p[2])
            
            if confidence < min_confidence:
                continue

            run = run + 1 if cls == prev else 1
            prev = cls
            if run >= consensus_window:
                result.append(p)
        return result

    def render_schedule(self) -> int:
        return 1