# from plugins.camera.camera_widget import CameraWidget
import os
import shutil
import tempfile
from pathlib import Path
from plugins.plugin_base import Plugin
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox
from PySide6.QtMultimedia import QMediaDevices, QCamera, QMediaCaptureSession, QMediaRecorder, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget

class CameraWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.video_container = QWidget()
        self.video_widget = QVideoWidget()
        self.device_select = QComboBox()
        self.refresh_devices()

        video_layout = QVBoxLayout()
        video_layout.setContentsMargins(2, 2, 2, 2)
        video_layout.addWidget(self.video_widget)
        self.video_container.setLayout(video_layout)

        self.btn_play = QPushButton("Start")
        self.btn_play.setProperty("variant", "primary")
        self.btn_play.clicked.connect(self.start_camera)

        control = QHBoxLayout()
        control.setContentsMargins(2, 0, 8, 6)
        control.setSpacing(3)
        control.addWidget(self.device_select, 1)
        control.addWidget(self.btn_play)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.video_container)
        layout.addLayout(control)

        self.camera  = QCamera()

        output_path = QUrl.fromLocalFile(os.path.join(tempfile.gettempdir(), "camera_output.mp4"))
        self.recorder = QMediaRecorder(outputLocation=output_path)
        self.recorder.recorderStateChanged.connect(self.on_recorder_changed)

        self.session = QMediaCaptureSession(camera=self.camera, videoOutput=self.video_widget, recorder=self.recorder)

        self.player = QMediaPlayer(videoOutput=self.video_widget)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)

    def refresh_devices(self):
        self.device_select.clear()
        for dev in QMediaDevices.videoInputs():
            self.device_select.addItem(dev.description(), dev)

    def _on_media_status_changed(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.player.pause()
            self.player.setPosition(self.player.duration())

    def refresh_ui(self):
        # Play/Stop button
        self.btn_play.setText("Stop" if self.camera.isActive() else "Start")
        self.btn_play.setProperty("variant", "danger" if self.camera.isActive() else "primary")
        self.btn_play.style().unpolish(self.btn_play)
        self.btn_play.style().polish(self.btn_play)
        self.btn_play.clicked.disconnect()
        self.btn_play.clicked.connect(self.stop_camera if self.camera.isActive() else self.start_camera)

        # Recording border
        self.video_container.setStyleSheet("border: 2px solid red" if self.recorder and self.recorder.recorderState() == QMediaRecorder.RecordingState else "")

    def start_camera(self):
        device = self.device_select.currentData()
        if device:
            self.session.setVideoOutput(self.video_widget)
            self.camera.setCameraDevice(device)
            self.camera.start()
            self.refresh_ui()

    def stop_camera(self):
        self.camera.stop()
        self.refresh_ui()

    def start_recording(self):
        if self.camera.isActive():
            self.recorder.record()

    def stop_recording(self, output_path: str):
        self.output_path = output_path
        self.recorder.stop()

    def on_recorder_changed(self, state):
        self.refresh_ui()
        if state == QMediaRecorder.StoppedState:
            source_file = self.recorder.outputLocation().toLocalFile()
            shutil.copy(source_file, self.output_path + '.mp4')

    def play_video(self, file_path: str):
        video_path = Path(file_path).with_suffix('.mp4')
        if video_path.exists():
            self.stop_camera()
            self.session.setVideoOutput(None)
            self.player.setVideoOutput(self.video_widget)
            self.player.setSource(QUrl.fromLocalFile(video_path))
            self.player.play()

class CameraPlugin(Plugin):
    name = "Camera"
    description = "A plugin for live video streaming, recording and playback"
    author = "Bellizzi, Gili"
    version = "1.0.0"

    """Camera plugin for live video streaming, recording and playback"""
    def __init__(self, api):
        super().__init__(api)
        self.camera_widget = None
        self.camera_widget = CameraWidget()
        self.camera_widget.setObjectName("CameraWidget")
        self.api.ui().add_dock("Camera", self.camera_widget, (1,1), position="below", relativeTo="Amplitude")
        self.api.styles().add_file("camera", "main", "plugins/camera/style.qss", priority=0)
        self.api.on_record_start.connect(self.camera_widget.start_recording)
        self.api.on_record_stop.connect(self.camera_widget.stop_recording)
        self.api.on_replay_start.connect(self.camera_widget.play_video)

    def deactivate(self):
        self.camera_widget.stop_camera()
        self.api.on_record_start.disconnect(self.camera_widget.start_recording)
        self.api.on_record_stop.disconnect(self.camera_widget.stop_recording)
        self.api.ui().remove_dock("Camera")
