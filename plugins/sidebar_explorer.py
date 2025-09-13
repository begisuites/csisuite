import qtawesome as qta
import socket
import threading
import time
from plugins.plugin_base import Plugin
from PySide6.QtCore import QMargins, QDir
from PySide6.QtWidgets import ( 
    QWidget, QVBoxLayout, QLabel, QFileSystemModel, QTreeView, QFrame
)
from services.ui import ToolbarPosition

class SidebarExplorer(Plugin):
    name = "Explorer"
    description = "A sidebar to explore files and directories."
    author = "Bellizzi, Gili"
    version = "1.0.0"

    def __init__(self, api):
        super().__init__(api)
        
        data_dir = QDir.currentPath() + "/data"
        for subdir in ["", "/datasets", "/saved"]:
            QDir().mkpath(data_dir + subdir)

        api.ui().add_sidebar_tab("Explorer", qta.icon("fa6s.folder", color="#ddd", color_active="#fff"), self.create_explorer_panel(), checked=True, icon_position=ToolbarPosition.TopStart)

    def deactivate(self):
        self.api.ui().remove_sidebar_tab("Explorer")

    def create_explorer_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel, spacing=0, contentsMargins=QMargins(0, 0, 0, 0))
        
        fsystem = QFileSystemModel(rootPath=QDir.currentPath())
        def create_tree_view(label, root_path):
            layout.addWidget(QLabel(label))
            tree = QTreeView(headerHidden=True, model=fsystem, rootIndex=fsystem.index(root_path))
            [tree.hideColumn(i) for i in range(1, 4)]  # Hide size, type, date modified
            tree.doubleClicked.connect(lambda index: 
                self.replay_file(fsystem.filePath(index)) if
                fsystem.filePath(index).endswith('.pcap') else None)
            layout.addWidget(tree)

        create_tree_view("DATASETS", f"{QDir.currentPath()}/data/datasets")
        layout.addWidget(QFrame(frameShape=QFrame.NoFrame, styleSheet="background-color: #3b3b3b; height:1px;", fixedHeight=1))
        create_tree_view("SAVED", f"{QDir.currentPath()}/data/saved")
        return panel
    
    def replay_file(self, file_path):
        # Start replaying .pcap file in new thread to avoid blocking the GUI
        def replay_async():
            self.api.on_replay_start.emit(file_path)
            with open(file_path, "rb") as f:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                while chunk := f.read(1024):
                    sock.sendto(chunk, ('127.0.0.1', 9000))
                    time.sleep(0.0001)
                sock.close()

        threading.Thread(target=replay_async).start()
