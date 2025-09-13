import logging

logger = logging.getLogger(__name__)

class NexmonCSIStreamReader:
    def __init__(self, host='0.0.0.0', port=5500, file=None, simulate_time=False, shift_fft=True, verbose=True, ts_as_datetime=True): ...
    def get_name(self) -> str : ...
    def __iter__(self): ...

try:
    from ._nexmon_fast import NexmonCSIStreamReader
    logger.info("Using fast NexmonCSIStreamReader")
except ImportError:
    from ._nexmon_fallback import NexmonCSIStreamReader
    logger.warning("Falling back to pure-Python NexmonCSIStreamReader")