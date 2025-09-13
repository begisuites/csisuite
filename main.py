import os
import sys
sys.dont_write_bytecode = True

import traceback
from PySide6 import QtCore
from PySide6.QtWidgets import QApplication
from application import Application

# Workaround to ignore pyqtgraph wrong warning
# This is a temporary fix until the issue is resolved in pyqtgraph
# See https://github.com/pyqtgraph/pyqtgraph/issues/3273
def qt_message_handler(mode, context, message):
    if "QObject::connect(QStyleHints, QStyleHints): unique connections require a pointer" in message:
        return 
    print(message)

if __name__ == '__main__':
    # Application setup
    app = QApplication([])

    # Ignore incorrect pyqtgraph warning
    QtCore.qInstallMessageHandler(qt_message_handler)

    # Main window setup
    try:
        win = Application(app)
        win.resize(1600, 800)
        win.show()
        win.start()
        sys.exit(app.exec())
    except Exception as e:
        print(f"❌ Failed to start application:")
        traceback.print_exc()
        os._exit(1)
