import time
import socket
import threading
import qtawesome as qta
from typing import List
from ui.toolbar import ToolbarPosition
from services.api import Api
from pyqtgraph.Qt import QtCore, QtWidgets
from plugins.plugin_base import Plugin
from utils.visualization import *
from PySide6.QtWidgets import (
    QToolButton, QMenu, QCheckBox, QLabel, QFileDialog, QWidget
)
from PySide6.QtGui import QAction

class Toolbar(Plugin):
    name = "Toolbar"
    description = "A basic toolbar plugin."
    author = "Bellizzi, Gili"
    version = "1.0.0"

    def __init__(self, api : Api):
        super().__init__(api)
        toolbar = api.ui().toolbar
        self.window = api.ui().get_window()
        self.ui_elements : List[QAction] = []

        # Toolbar - "File" button to read existing .pcap files
        file_button = QToolButton(popupMode=QToolButton.InstantPopup)
        file_button.setText("File")
        self.file_menu = QMenu()
        open_action = QAction("Open...", self.window)
        open_action.triggered.connect(self.open_file_dialog)
        save_action = QAction("Save As...", self.window)
        save_action.triggered.connect(self.save_file_dialog)
        self.file_menu.addAction(open_action)
        self.file_menu.addAction(save_action)
        file_button.setMenu(self.file_menu)
        self.ui_elements.append(toolbar.add_widget(file_button, ToolbarPosition.LeftEnd))

        # Toolbar - "Enable simulation mode" to toggle time simulation
        self.sim_checkbox = QCheckBox("Enable simulation mode")
        self.sim_checkbox.setChecked(self.api.csi().reader.simulate_time)  # Default unchecked
        self.sim_checkbox.toggled.connect(lambda checked: setattr(self.api.csi().reader, 'simulate_time', checked))
        self.ui_elements.append(toolbar.add_widget(self.sim_checkbox, ToolbarPosition.LeftEnd))

        # Toolbar - Mac dropdown to select the MAC address
        self.mac_dropdown = QtWidgets.QComboBox()
        self.mac_dropdown.setToolTip("Select MAC address to visualize")
        self.mac_dropdown.addItem('No MAC selected')
        self.mac_dropdown.setEnabled(False)
        self.mac_dropdown.currentTextChanged.connect(lambda mac: self.api.csi().set_selected_mac(mac if mac else None))
        self.ui_elements.append(toolbar.add_widget(self.mac_dropdown, ToolbarPosition.CenterStart))

        # Toolbar - Model
        self.model_dropdown = QtWidgets.QComboBox()
        self.model_dropdown.setToolTip("Select model")
        self.model_dropdown.addItem('No model selected')
        self.model_dropdown.currentTextChanged.connect(lambda model: self.api.models().set_selected_model(model if model else None))
        self.ui_elements.append(toolbar.add_widget(self.model_dropdown, ToolbarPosition.CenterStart))

        # Toolbar - "Clear" button to clear the current CSI data
        self.action_clear = QAction(qta.icon("fa6s.eraser", color="#ddd", color_active="#fff"), "Clear CSI")
        self.action_clear.triggered.connect(self.clear)
        self.ui_elements.append(toolbar.add_action(self.action_clear, ToolbarPosition.RightEnd))

        # Toolbar - Pause/Resume buttons to control the data stream
        self.pause_action = QAction(qta.icon("fa6s.pause", color="#ddd", color_active="#fff"), "Pause")
        self.resume_action = QAction(qta.icon("fa6s.play", color="#ddd", color_active="#fff"), "Resume", visible=False)
        self.pause_action.triggered.connect(lambda: self.api.csi().reader.receiver.pause())
        self.resume_action.triggered.connect(lambda: self.api.csi().reader.receiver.resume())
        self.ui_elements.append(toolbar.add_action(self.pause_action, ToolbarPosition.RightEnd))
        self.ui_elements.append(toolbar.add_action(self.resume_action, ToolbarPosition.RightEnd))

        # Toolbar - Listening status
        self.status_circle = QLabel()
        self.status_circle.setFixedSize(28, 12)
        self.status_circle.setStyleSheet("border-radius: 60px;")
        self.status_label = QLabel("Listening on 0.0.0.0:9000", alignment=QtCore.Qt.AlignVCenter)
        self.status_label.setStyleSheet("margin-left: 0px;")
        self.status_received = QLabel("Received: 0 B", alignment=QtCore.Qt.AlignVCenter)
        self.status_received.setFixedWidth(130)
        self.status_window = QLabel("Window: 0", alignment=QtCore.Qt.AlignVCenter)
        self.status_window.setFixedWidth(115)
        self.ui_elements.append(toolbar.add_widget(self.status_circle, ToolbarPosition.RightEnd))
        self.ui_elements.append(toolbar.add_widget(self.status_label, ToolbarPosition.RightEnd))
        self.ui_elements.append(toolbar.add_separator(ToolbarPosition.RightEnd))
        self.ui_elements.append(toolbar.add_widget(self.status_received, ToolbarPosition.RightEnd))
        self.ui_elements.append(toolbar.add_separator(ToolbarPosition.RightEnd))
        self.ui_elements.append(toolbar.add_widget(self.status_window, ToolbarPosition.RightEnd))

    def deactivate(self):
        for element in self.ui_elements:
            self.api.ui().toolbar.remove(element)

    def stream_file(self, file_path):
        # Start streaming .pcap file in new thread to avoid blocking the GUI
        port = self.api.csi().reader.port

        def stream_async():
            with open(file_path, "rb") as f:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                while chunk := f.read(2048):
                    sock.sendto(chunk, ('127.0.0.1', port))
                    time.sleep(0.00001)
                sock.close()
        threading.Thread(target=stream_async).start()

    def open_file_dialog(self):
        # Streams data from the selected .pcap file
        file_path, _ = QFileDialog.getOpenFileName(self.window, "Open File", "", "PCAP (*.pcap)")
        if file_path:
            self.stream_file(file_path)

    def save_file_dialog(self):
        # Save the current CSI data to a .pcap file
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_name = f"saved/csi_{timestamp}.pcap"
        file_path, _ = QFileDialog.getSaveFileName(self.window, "Save File", default_name, "PCAP (*.pcap)")
        if file_path:
            self.save_file(file_path)

    def save_file(self, file_path):
        with open(file_path, "wb") as f:
            self.api.csi().reader.receiver.save(file_path)

    def clear(self):
        self.api.csi().clear()
        self.mac_dropdown.clear()
        self.mac_dropdown.addItem('No MAC selected')
        self.mac_dropdown.setEnabled(False)
        self.api.csi().reader.receiver.clear()
        self.api.models().clear_predictions()

    def render_schedule(self):
        return 1
    
    def render(self, tick):
        host, port = self.api.csi().reader.host, self.api.csi().reader.port
        macs = self.api.csi().get_macs()
        ts_data = self.api.csi().get_ts()

        # Add macs to dropdown if not exists
        for mac in macs:
            if not self.mac_dropdown.isEnabled():
                self.mac_dropdown.removeItem(0)  # Remove "No MAC selected"
                self.mac_dropdown.setEnabled(True)
            if self.mac_dropdown.findText(mac) < 0:
                self.mac_dropdown.addItem(mac)

        # Add models to dropdown
        for model in self.api.models().get_models():
            if self.model_dropdown.findText(model.get_name()) < 0:
                self.model_dropdown.addItem(model.get_name())

        # Listening status
        self.status_label.setText(f"Listening on {host}:{port}")
        self.status_received.setText(f"Received: {human_readable_bytes(len(self.api.csi().reader.receiver.data))}")
        self.status_window.setText(f"Window: {len(ts_data)}  ")
        if self.api.csi().reader.receiver.is_paused:
            self.status_circle.setStyleSheet("background-color: red; border-radius: 6px;")
        else:
            self.status_circle.setStyleSheet("background-color: green; border-radius: 6px;")

        # Pause/Resume actions
        self.pause_action.setVisible(not self.api.csi().reader.receiver.is_paused)
        self.resume_action.setVisible(self.api.csi().reader.receiver.is_paused)