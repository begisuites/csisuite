from pyqtgraph.Qt import QtWidgets
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QSize, QMargins
from PySide6.QtWidgets import (
    QButtonGroup,
    QWidget,
    QStackedWidget,
    QToolButton,
    QSplitter,
    QVBoxLayout
)
from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea

from ui.toolbar import Toolbar, ToolbarPosition

class UI:
    """
    An interface to manage the user interface for the WiFi-HAR application.
    """
    def __init__(self, window: QtWidgets.QMainWindow):
        self.window = window
        self.icon_toolbar = Toolbar(window, "IconToolbar", Qt.ToolBarArea.LeftToolBarArea, Qt.Orientation.Vertical, iconSize=QSize(24, 24))

        # Right dock area
        self.dockArea = DockArea()
        self.docks = {}

        # Left sidebar
        self.sidebar = QStackedWidget(objectName="Sidebar", minimumWidth=200)
        self._tabs = {}            # name -> (btn, widget, action)
        self._btn_group = QButtonGroup(window)
        self._btn_group.setExclusive(True)

        # Splitter to hold sidebar and dock area
        self.splitter = QSplitter(Qt.Horizontal, handleWidth=0)
        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.dockArea)
        self.splitter.setSizes([3, 900])

        self.central_widget = QWidget()
        layout = QVBoxLayout(self.central_widget, spacing=0, contentsMargins=QMargins(0, 0, 0, 0))
        layout.addWidget(self.splitter)
        window.setCentralWidget(self.central_widget)

        # Shared plots
        self.plots = {}

        # Toolbar
        self.toolbar : Toolbar = Toolbar(window, "MainToolbar", Qt.ToolBarArea.TopToolBarArea, Qt.Orientation.Horizontal)

    def select_sidebar(self, name: str):
        _, widget, _ = self._tabs[name]
        idx = self.sidebar.indexOf(widget)
        if idx != -1:
            # make sure sidebar is visible/wide enough
            sizes = self.splitter.sizes()
            if(sizes[0] < 200):
                self.splitter.setSizes([200, sizes[1]])
            self.sidebar.setCurrentIndex(idx)

    def add_sidebar_tab(self, name: str, icon: QIcon, widget: QWidget, checked: bool = False, icon_position: ToolbarPosition = ToolbarPosition.TopEnd):
        """Create a sidebar tab with a button and add it to the sidebar."""
        widget.setObjectName(name)
        btn = QToolButton(icon=icon, toolTip=name, checkable=True, objectName=f"btn_{name}")
        btn.clicked.connect(lambda _checked, n=name: self.select_sidebar(n))
        btn.setProperty("sidebarButton", True)
        btn.setChecked(checked)
        self._btn_group.addButton(btn)

        action = self.icon_toolbar.add_widget(btn, icon_position)
        self.sidebar.addWidget(widget)

        self._tabs[name] = (btn, widget, action)

        if checked:
            self.select_sidebar(name)

    def remove_sidebar_tab(self, name: str) -> bool:
        """Revert everything done by add_sidebar_tab for this tab."""
        data = self._tabs.pop(name, None)
        if not data:
            return False

        btn, widget, action = data

        # 1) Disconnect & remove button
        btn.clicked.disconnect()
        self._btn_group.removeButton(btn)
        self.icon_toolbar.remove(action)
        btn.deleteLater()

        # 2) Remove the widget from the stacked sidebar
        self.sidebar.removeWidget(widget)
        widget.deleteLater()

        # 3) Restore selection / collapse if no tabs remain
        if self._tabs:
            # pick any remaining tab deterministically
            next_name = next(iter(self._tabs.keys()))
            next_btn, _, _ = self._tabs[next_name]
            next_btn.setChecked(True)
            self.select_sidebar(next_name)
    
    def add_dock(self, name, widget, size, position, relativeTo=None, autoOrientation=False):
        dock = Dock(name, size=size, autoOrientation=autoOrientation)
        dock.addWidget(widget)
        self.docks[name] = {'dock': dock, 'position': position, 'relativeTo': relativeTo, 'built': False}

    def get_dock(self, name: str) -> Dock:
        if name not in self.docks:
            raise ValueError(f"Dock with name '{name}' does not exist.")
        return self.docks[name]['dock']

    def is_dock_visible(self, name: str) -> bool:
        if name not in self.docks:
            return False
        return self.docks[name]['dock'].isVisible()

    def add_plot(self, name: str, plot):
        if name in self.plots:
            raise ValueError(f"Plot with name '{name}' already exists.")
        self.plots[name] = plot

    def remove_plot(self, name: str):
        if name not in self.plots:
            return
        del self.plots[name]

    def remove_dock(self, name: str):
        if name not in self.docks:
            return
        dock_info = self.docks[name]
        dock_info['dock'].close()
        del self.docks[name]

    def get_plot(self, name: str):
        if name not in self.plots:
            raise ValueError(f"Plot with name '{name}' does not exist.")
        return self.plots[name]

    def get_window(self):
        return self.window

    def build(self):
        built = 1
        while built > 0 and any(not info['built'] for info in self.docks.values()):
            built = 0
            for info in self.docks.values():
                if info['built']:
                    continue
                relativeTo = None
                if isinstance(info['relativeTo'], str):
                    if not self.docks[info['relativeTo']]['built']:
                        continue
                    relativeTo = self.docks[info['relativeTo']]['dock']

                self.dockArea.addDock(info['dock'], info['position'], relativeTo)
                info['built'] = True
                built += 1

        pending = [name for name, info in self.docks.items() if not info['built']]
        if pending:
            raise ValueError(f'Circular or invalid dock dependencies: {pending}')