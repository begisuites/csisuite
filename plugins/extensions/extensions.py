import qtawesome as qta
import numpy as np
from plugins.plugin_base import Plugin
from utils.visualization import *
from PySide6.QtCore import Qt, QMargins
from PySide6.QtWidgets import ( 
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame, QPushButton, QCheckBox
)

class Extensions(Plugin):
    name = "Plugins Manager"
    description = "A plugin to visualize the energy distribution of the data."
    author = "Bellizzi, Gili"
    version = "1.0.0"
    is_manageable = False

    def __init__(self, api):
        super().__init__(api)
        self.plugin_items: dict[str, tuple[Plugin, QLabel, QPushButton]] = {}
        api.ui().add_sidebar_tab("Plugins", qta.icon("fa6s.puzzle-piece", color="#ddd", color_active="#fff"), self.create_plugins_panel())
        self.api.styles().add_file("extensions", "main", "plugins/extensions/style.qss", priority=0)
        self.show_ms_perf = False

    def deactivate(self):
        self.api.ui().remove_sidebar_tab("Plugins")

    def create_plugins_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel, spacing=0, contentsMargins=QMargins(0, 0, 0, 0), alignment=Qt.AlignTop)

        title_label = QLabel("PLUGINS")
        layout.addWidget(title_label)

        plugins = QWidget(objectName="PluginsScrollArea")
        self.plugins_layout = QVBoxLayout(plugins, spacing=0, contentsMargins=QMargins(0, 0, 0, 0), alignment=Qt.AlignTop)
        for name, plugin in self.api.plugins().get_all_plugins():
            self.add_plugin_item(plugin, name, self.plugins_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(plugins)
        layout.addWidget(scroll_area)

        layout.addWidget(QFrame(frameShape=QFrame.NoFrame, styleSheet="background-color: #3b3b3b;", fixedHeight=1))
        show_ms_perf = QCheckBox("Show CPU time (ms)")
        show_ms_perf.setStyleSheet("margin: 10px 0px 5px 5px;")
        show_ms_perf.setToolTip("Show CPU time consumed by each plugin on the last 100 render cycles. If disabled, the percentage of CPU usage in relative terms will be shown instead.")
        show_ms_perf.checkStateChanged.connect(lambda state: setattr(self, 'show_ms_perf', state == Qt.Checked) or self.render(0))
        layout.addWidget(show_ms_perf)
        return panel
    
    def add_plugin_item(self, plugin: Plugin, plugin_name: str, parent_layout: QVBoxLayout):
        item = QWidget()
        item.setProperty("class", "plugin-item")
        name = QLabel(f"{plugin.name}")
        name.setToolTip(f"{plugin.description}\n\nVersion: {plugin.version}\nAuthor: {plugin.author}")
        usage = QLabel()
        button = QPushButton("Disable")

        if not plugin.is_manageable:
            button.setProperty("variant", "invisible")
        else:
            button.setProperty("variant", "danger")
            button.clicked.connect(lambda: self.toggle_plugin(plugin_name))
            
        layout = QHBoxLayout(item, spacing=0, contentsMargins=QMargins(0, 2, 5, 2))
        layout.addWidget(name, 1)
        layout.addWidget(usage)
        layout.addWidget(button)

        if not plugin.is_manageable:
            parent_layout.insertWidget(0,item)
            parent_layout.insertWidget(1, QFrame(frameShape=QFrame.NoFrame, styleSheet="background-color: #3b3b3b;", fixedHeight=1))
        else:
            parent_layout.addWidget(item)
            parent_layout.addWidget(QFrame(frameShape=QFrame.NoFrame, styleSheet="background-color: #3b3b3b;", fixedHeight=1))

        self.plugin_items[plugin_name] = (plugin, usage, button)

    def build(self):
        self.render(0)

    def render(self, tick):
        # Collect performance data for the last 100 calls
        stats = []
        total_time = 0.0

        for name, plugin in self.api.plugins().get_all_plugins():
            total_time += np.sum(plugin.perf_ticks)
            stats.append((name, plugin, plugin.perf_ticks))

        # Display each plugin with % usage
        for name, plugin, ticks in sorted(stats, key=lambda x: np.mean(x[2]) if len(x[2]) > 0 else 0, reverse=True):
            total_ms = np.sum(ticks) * 1000 if len(ticks) else 0
            pct = (total_ms / (total_time * 1000)) * 100 if total_time > 0 else 0

            if not name in self.plugin_items:
                self.add_plugin_item(plugin, name, self.plugins_layout)

            _, usage_label, _ = self.plugin_items[name]
            if pct > 1 or self.show_ms_perf:
                usage_label.setText(f'{total_ms:.0f}ms' if self.show_ms_perf else f'{pct:.0f}%')
            else:
                usage_label.setText('')

    def toggle_plugin(self, name: str):
        plugin, usage_label, button = self.plugin_items[name]
        usage_label.setText('')
        button.setText("Enable" if button.text() == "Disable" else "Disable")
        button.setProperty("variant", "primary" if button.text() == "Enable" else "danger")
        button.style().unpolish(button)
        button.style().polish(button)

        if button.text() == "Disable":
            self.api.plugins().load_plugin(plugin.plugin_file)
            self.api.ui().build()
        else:
            self.api.plugins().unload_plugin(name)

    def render_schedule(self) -> int:
        return 50