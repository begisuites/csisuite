from typing import Dict
import qtawesome as qta
from utils.configurable import Configurable
from plugins.plugin_base import Plugin
from PySide6.QtCore import Qt, QMargins
from PySide6.QtWidgets import ( QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, QSpinBox, QCheckBox, QLineEdit)
from services.ui import ToolbarPosition

class SidebarSettings(Plugin):
    name = "Settings"
    description = "A sidebar to adjust settings."
    author = "Bellizzi, Gili"
    version = "1.0.0"
    is_manageable = False

    def __init__(self, api):
        super().__init__(api)
        self.configs : Dict[str, QVBoxLayout] = {}
        self.api.styles().add_file("settings", "main", "plugins/settings/style.qss", priority=0)
        api.ui().add_sidebar_tab("Settings", qta.icon("fa6s.gear", color="#ddd", color_active="#fff"), self.create_settings_panel(), icon_position=ToolbarPosition.BottomEnd)

    def deactivate(self):
        self.api.ui().remove_sidebar_tab("Settings")

    def create_settings_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel, spacing=0, contentsMargins=QMargins(0, 0, 0, 0), alignment=Qt.AlignTop)
        layout.addWidget(QLabel("SETTINGS"))

        self.configs_scroll = QWidget(objectName="ConfigsScrollArea")
        self.filters_layout = QVBoxLayout(self.configs_scroll, spacing=0, contentsMargins=QMargins(0, 0, 0, 0), alignment=Qt.AlignTop)
        layout.addWidget(self.configs_scroll)
        return panel
    
    def add_config_item(self, config_name: str, config: Configurable, parent_layout: QVBoxLayout):
        item = QWidget()
        item.setProperty("class", "config-item")
        name = QLabel(f"{config_name}")
        
        layout = QVBoxLayout(item, spacing=0, contentsMargins=QMargins(0, 5, 0, 5))
        layout.addWidget(name)

        config_constraints = config.get_config_constraints()
        for key, (min_val, max_val) in config_constraints.items():
            config_item = QWidget()
            config_layout = QHBoxLayout(config_item, spacing=5, contentsMargins=QMargins(0, 0, 5, 0))
            label = QLabel(key)
            config_layout.addWidget(label)

            if isinstance(config.get(key), bool):
                check = QCheckBox()
                check.setChecked(config.get(key))
                check.stateChanged.connect(lambda state, k=key: config.set(k, state == Qt.Checked))
                config_layout.addWidget(check)

            if isinstance(config.get(key), float) or isinstance(config.get(key), int):
                spin = QDoubleSpinBox(singleStep=0.1) if isinstance(config.get(key), float) else QSpinBox()
                spin.setRange(min_val, max_val)
                spin.setValue(config.get(key))
                spin.valueChanged.connect(lambda value, k=key: config.set(k, value))
                config_layout.addWidget(spin)

            if isinstance(config.get(key), str):
                line_edit = QLineEdit()
                line_edit.setText(config.get(key))
                line_edit.textChanged.connect(lambda text, k=key: config.set(k, text))
                config_layout.addWidget(line_edit)

            layout.addWidget(config_item)

        parent_layout.addWidget(item)
        parent_layout.addWidget(QFrame(frameShape=QFrame.NoFrame, styleSheet="background-color: #3b3b3b;", fixedHeight=1))
        self.configs[config_name] = layout
    
    def render_schedule(self) -> int:
        return 50
    
    def render(self, tick):
        for config_name, config in self.api.settings().get_all().items():
            if not config_name in self.configs:
                self.add_config_item(config_name, config, self.filters_layout)
