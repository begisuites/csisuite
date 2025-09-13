from datetime import datetime
import pyqtgraph as pg

class MinuteSecondAxis(pg.DateAxisItem):
    def tickStrings(self, values, scale, spacing):
        return [datetime.fromtimestamp(value).strftime("%M:%S") for value in values]
    
def human_readable_bytes(num_bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num_bytes < 1024:
            return f"{num_bytes:.2f} {unit}" if unit != 'B' and unit != 'KB' else f"{num_bytes:.0f} {unit}"
        num_bytes /= 1024

    return f"{num_bytes:.2f} PB"