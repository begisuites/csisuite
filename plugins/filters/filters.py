import qtawesome as qta
import numpy as np
from filters.filter_base import Filter
from plugins.plugin_base import Plugin
from utils.visualization import *
from PySide6.QtCore import Qt, QMargins
from PySide6.QtWidgets import ( 
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame, QPushButton, QCheckBox, QSpinBox, QDoubleSpinBox
)

class Filters(Plugin):
    name = "Filters Manager"
    description = "A filter to visualize and manage the filters applied to the CSI."
    author = "Bellizzi, Gili"
    version = "1.0.0"

    def __init__(self, api):
        super().__init__(api)
        self.filter_items: dict[str, tuple[Filter, QLabel, QPushButton]] = {}
        api.ui().add_sidebar_tab("Filters", qta.icon("fa6s.filter", color="#ddd", color_active="#fff"), self.create_filters_panel())
        self.api.styles().add_file("filters", "main", "plugins/filters/style.qss", priority=0)
        self.show_ms_perf = False

    def deactivate(self):
        self.api.ui().remove_sidebar_tab("Filters")

    def create_filters_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel, spacing=0, contentsMargins=QMargins(0, 0, 0, 0), alignment=Qt.AlignTop)

        title_label = QLabel("FILTERS")
        layout.addWidget(title_label)

        filters = QWidget(objectName="FiltersScrollArea")
        self.filters_layout = QVBoxLayout(filters, spacing=0, contentsMargins=QMargins(0, 0, 0, 0), alignment=Qt.AlignTop)
        for filter in self.api.csi().filters.get_filters():
            self.add_filter_item(filter, filter.name, self.filters_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(filters)
        layout.addWidget(scroll_area)

        layout.addWidget(QFrame(frameShape=QFrame.NoFrame, styleSheet="background-color: #3b3b3b;", fixedHeight=1))
        show_ms_perf = QCheckBox("Show CPU time (ms)")
        show_ms_perf.setStyleSheet("margin: 10px 0px 5px 5px;")
        show_ms_perf.setToolTip("Show CPU time consumed by each filter on the last 100 render cycles. If disabled, the percentage of CPU usage in relative terms will be shown instead.")
        show_ms_perf.checkStateChanged.connect(lambda state: setattr(self, 'show_ms_perf', state == Qt.Checked) or self.render(0))
        layout.addWidget(show_ms_perf)
        return panel

    def add_filter_item(self, filter: Filter, filter_name: str, parent_layout: QVBoxLayout):
        item = QWidget()
        item.setProperty("class", "filter-item")
        name = QLabel(f"{filter.name}")
        name.setToolTip(f"{filter.description}\n\nVersion: {filter.version}\nAuthor: {filter.author}")
        usage = QLabel()
        button = QPushButton("Enable")

        button.setProperty("variant", "danger" if filter.is_enabled() else "primary")
        button.clicked.connect(lambda: self.toggle_filter(filter_name))

        layout = QVBoxLayout(item, spacing=0, contentsMargins=QMargins(0, 5, 0, 5))
        header = QWidget()
        header_layout = QHBoxLayout(header, spacing=0, contentsMargins=QMargins(0, 0, 5, 0))
        header_layout.addWidget(name, 1)
        header_layout.addWidget(usage)
        header_layout.addWidget(button)
        layout.addWidget(header)

        config = filter.get_config_constraints()
        for key, (min_val, max_val) in config.items():
            config_item = QWidget()
            config_layout = QHBoxLayout(config_item, spacing=0, contentsMargins=QMargins(0, 0, 5, 0))
            label = QLabel(key)
            config_layout.addWidget(label)

            val_spin = QDoubleSpinBox(singleStep=0.1) if isinstance(filter.get(key), float) else QSpinBox()
            val_spin.setValue(filter.get(key))
            val_spin.setRange(min_val, max_val)
            val_spin.valueChanged.connect(lambda value, k=key: filter.set(k, value))
            config_layout.addWidget(val_spin)

            layout.addWidget(config_item)

        parent_layout.addWidget(item)

        parent_layout.addWidget(QFrame(frameShape=QFrame.NoFrame, styleSheet="background-color: #3b3b3b;", fixedHeight=1))
        self.filter_items[filter_name] = (filter, usage, button)

    def render(self, tick):
        # Collect performance data for the last 100 calls
        stats = []
        total_time = 0.0

        for filter in self.api.csi().filters.get_filters():
            total_time += np.sum(filter.perf_ticks)
            stats.append((filter.name, filter, filter.perf_ticks))

        # Display each filter with % usage
        for name, filter, ticks in sorted(stats, key=lambda x: np.mean(x[2]) if len(x[2]) > 0 else 0, reverse=True):
            total_ms = np.sum(ticks) * 1000 if len(ticks) else 0
            pct = (total_ms / (total_time * 1000)) * 100 if total_time > 0 else 0

            if not name in self.filter_items:
                self.add_filter_item(filter, name, self.filters_layout)

            _, usage_label, _ = self.filter_items[name]
            if filter.is_enabled() and (pct > 1 or self.show_ms_perf):
                usage_label.setText(f'{total_ms:.0f}ms' if self.show_ms_perf else f'{pct:.0f}%')
            else:
                usage_label.setText('')

    def render_schedule(self) -> int:
        return 50
    
    def toggle_filter(self, filter_name: str):
        filter, usage_label, button = self.filter_items[filter_name]
        usage_label.setText('')
        button.setText("Enable" if button.text() == "Disable" else "Disable")
        button.setProperty("variant", "primary" if button.text() == "Enable" else "danger")
        button.style().unpolish(button)
        button.style().polish(button)
        filter.set_enabled(not filter.is_enabled())
