from datetime import datetime
import qtawesome as qta
from ui.toolbar import ToolbarPosition
from services.api import Api
from plugins.plugin_base import Plugin
from pyqtgraph.Qt import QtCore
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import (
    QToolButton, QVBoxLayout, QCheckBox, QApplication,
    QLabel, QWidget, QLineEdit, 
    QHBoxLayout, QSpinBox, QPushButton
)

class Recording(Plugin):
    name = "Recording"
    description = "A plugin to record the CSI data."
    author = "Bellizzi, Gili"
    version = "1.0.0"

    def __init__(self, api : Api):
        super().__init__(api)
        self.api = api
        self.recording = False
        self.file_path = None

        # Toolbar - Record button
        self.record_popup = RecordPopup(api.ui().get_window())
        self.record_button = QToolButton(icon=qta.icon("fa6s.camera", color="#ddd", color_active="#fff"))
        self.record_button.clicked.connect(self.show_record_popup)
        self.record_popup.confirm_btn.clicked.connect(lambda: self.record(self.record_popup.record_duration_spin.value()))
        self.record_popup_action = api.ui().toolbar.add_widget(self.record_button, position=ToolbarPosition.RightStart)

    def deactivate(self):
        self.api.ui().toolbar.remove(self.record_popup_action)

    def show_record_popup(self):
        btn_pos = self.record_button.mapToGlobal(QPoint(0, self.record_button.height()))
        self.record_popup.move(btn_pos)
        self.record_popup.show()

    def record(self, duration):
        self.record_loops_total = self.record_popup.loop_spin.value()
        self.record_loops_current = 0
        self.start_recording(duration)
        
    def start_recording(self, duration):
        # Start recording the current CSI data for a specified duration
        self.record_button.setIcon(qta.icon("fa6s.stop", color="green", animation=qta.Pulse(self.record_button)))

        self.record_duration = duration
        self.api.csi().reader.receiver.pause()
        self.api.csi().clear()
        self.api.csi().reader.receiver.resume()
        self.api.on_record_start.emit()
        QApplication.beep()
        QtCore.QTimer.singleShot(duration * 1000, self.stop_recording)

    def stop_recording(self):
        # Stop recording the current CSI data
        self.api.csi().reader.receiver.pause()
        QApplication.beep()
        QtCore.QTimer.singleShot(120, QApplication.beep)

        if self.record_popup.save_checkbox.isChecked():
            # Save the recorded data automatically
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            label_prefix = self.record_popup.label_input.text() or "csi"
            file_path = f"data/saved/{label_prefix}_{timestamp}"
            self.save_file(file_path + ".pcap")
            self.api.on_record_stop.emit(file_path)

        self.record_loops_current += 1
        if self.record_loops_current < self.record_loops_total:
            delay = self.record_popup.delay_spin.value()
            self.record_button.setIcon(qta.icon("fa6s.stop", color="yellow", animation=qta.Spin(self.record_button)))
            QtCore.QTimer.singleShot(delay * 1000, lambda: self.start_recording(self.record_duration))
        else:
            self.record_button.setIcon(qta.icon("fa6s.camera", color="#ddd", color_active="#fff"))

    def save_file(self, file_path):
        with open(file_path, "wb") as f:
            self.api.csi().reader.receiver.save(file_path)

class RecordPopup(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setLayout(QVBoxLayout(spacing=8))
        self.layout().setContentsMargins(10, 10, 10, 10)
        
        self.label_input = QLineEdit(placeholderText="Enter label prefix...")
        self.loop_spin = QSpinBox(value=1, minimum=1, maximum=100)
        self.delay_spin = QSpinBox(value=3, minimum=1, maximum=60, suffix=" sec")
        self.record_duration_spin = QSpinBox(value=3, minimum=1, maximum=30, suffix=" sec")
        self.save_checkbox = QCheckBox("Save after capture", checked=True)
        self.confirm_btn = QPushButton("Start")

        self._addLayout("Label:", self.label_input)
        self._addLayout("Loops:", self.loop_spin)
        self._addLayout("Delay:", self.delay_spin)
        self._addLayout("Duration:", self.record_duration_spin)
        self.layout().addWidget(self.save_checkbox)
        self.layout().addWidget(self.confirm_btn)
    
    def _addLayout(self, label, widget):
        layout = QHBoxLayout()
        layout.addWidget(QLabel(label))
        layout.addWidget(widget)
        self.layout().addLayout(layout)