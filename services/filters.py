import numpy as np
import numpy.typing as npt
from pathlib import Path
from typing import List
import importlib
import time
from importlib.machinery import ModuleSpec
import importlib.util
from filters.filter_base import Filter

class Filters():
    def __init__(self):
        self.filters : List[Filter] = []

    def add_filter(self, filter: Filter):
        self.filters.append(filter)

    def get_filters(self):
        return self.filters

    def apply_filters(self, amp: npt.NDArray[np.float32], phase: npt.NDArray[np.float32], ts: List[float]):
        for filter in self.filters:
            start = time.perf_counter()
            if filter.is_enabled():
                filter.apply(amp, phase, ts)
            elapsed = time.perf_counter() - start
            filter.add_performance_time(elapsed)

    def load_filters(self, directory: Path):
        for filter_file in directory.iterdir():
            if filter_file.is_file() and filter_file.suffix == '.py':
                self.load_filter(filter_file)
            if filter_file.is_dir():
                self.load_filters(filter_file)

    def load_filter(self, filter_file: Path):
        try:
            filter_name = Path(filter_file).absolute().relative_to(Path.cwd()).as_posix()
            spec = importlib.util.spec_from_file_location(filter_name, filter_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            filters = [obj for obj in vars(module).values() if isinstance(obj, type) and issubclass(obj, Filter) and obj is not Filter]
            
            if not filters:
                return
            elif len(filters) > 1:
                raise ValueError(f"❌ Multiple filters found in {filter_file}: {', '.join([f.__name__ for f in filters])}")
            
            filter = filters[0]()
            self.add_filter(filter)
            print(f"🔧 Loaded filter {filter_name}")
        except Exception as e:
            print(f"❌ Failed to load filter from {filter_file}: {e}")
