from enum import Enum
from pyqtgraph.Qt import QtCore, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSizePolicy, QWidget, QToolBar
from PySide6.QtGui import QAction

class ToolbarPosition(Enum):
    LeftStart = "left_start"
    LeftEnd = "left_end"
    CenterStart = "center_start"
    CenterEnd = "center_end"
    RightStart = "right_start"
    RightEnd = "right_end"
    TopStart = "top_start"
    TopEnd = "top_end"
    BottomStart = "bottom_start"
    BottomEnd = "bottom_end"

class Toolbar():
    def __init__(self, window: QtWidgets.QMainWindow, name: str, area: Qt.ToolBarArea, orientation: Qt.Orientation, iconSize=QtCore.QSize(18, 18)):
        super().__init__()
        self.window = window
        self.toolbar = QToolBar(objectName=name, orientation=orientation, movable=False, contextMenuPolicy=Qt.PreventContextMenu)
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(iconSize)
        window.addToolBar(area, self.toolbar)

        # Toolbar is divided into three sections: Left, Center, Right
        self.anchors = {}
        spacer_left = QWidget()
        spacer_left.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        spacer_right = QWidget()
        spacer_right.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Add anchors and spacers to toolbar
        for pos in [ToolbarPosition.LeftStart, ToolbarPosition.LeftEnd, ToolbarPosition.TopStart, ToolbarPosition.TopEnd]:
            self.anchors[pos] = self.toolbar.addWidget(QWidget(visible=False))
        
        self.toolbar.addWidget(spacer_left)

        for pos in [ToolbarPosition.CenterStart, ToolbarPosition.CenterEnd]:
            self.anchors[pos] = self.toolbar.addWidget(QWidget(visible=False))
        
        self.toolbar.addWidget(spacer_right)

        for pos in [ToolbarPosition.RightStart, ToolbarPosition.RightEnd, ToolbarPosition.BottomStart, ToolbarPosition.BottomEnd]:
            self.anchors[pos] = self.toolbar.addWidget(QWidget(visible=False))

    def add_widget(self, widget: QWidget, position: ToolbarPosition) -> QAction:
        return self.toolbar.insertWidget(self.anchors[position], widget)

    def add_action(self, action: QAction, position: ToolbarPosition) -> QAction:
        self.toolbar.insertAction(self.anchors[position], action)
        return action

    def add_separator(self, position: ToolbarPosition) -> QAction:
        return self.toolbar.insertSeparator(self.anchors[position])
    
    def remove(self, action: QAction):
        self.toolbar.removeAction(action)