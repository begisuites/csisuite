import numpy as np
import importlib.util
from pathlib import Path
from services.csi import CSI
from models.model_base import HARModel

class Models():
    def __init__(self, num_classes: int):
        self.num_classes = num_classes
        self.models : dict[str, HARModel] = {}
        self.selected_model = None
        self.predictions : list[(float, float, np.ndarray)] = []
        self.last_prediction : float = 0.0
        self.classes = [ 'fall', 'quiet', 'sit_down', 'stand_up', 'walk' ]

    def load_models(self, api, directory: Path):
        """Load all models from the models folder recursively"""
        for plugin_file in directory.iterdir():
            if plugin_file.is_file() and plugin_file.suffix == '.py':
                self._load_model(api, plugin_file)
            if plugin_file.is_dir():
                self.load_models(api, plugin_file)
    
    def _load_model(self, api, model_file: Path):
        try:
            model_name = Path(model_file).absolute().relative_to(Path.cwd()).as_posix()
            spec = importlib.util.spec_from_file_location(model_name, model_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            models = [obj for obj in vars(module).values() if isinstance(obj, type) and issubclass(obj, HARModel) and obj is not HARModel]

            if not models:
                return

            for model_class in models:
                model = model_class(api, self.num_classes)
                self.add_model(model.get_name(), model)
                print(f"✨ Loaded model {model.get_name()}")
        except Exception as e:
            print(f"❌ Failed to load model {model_name}: {e}")

    def get_model(self, model_name: str) -> HARModel:
        return self.models[model_name] if model_name in self.models else None

    def get_models(self) -> list[HARModel]:
        return list(self.models.values())

    def get_selected_model(self) -> HARModel:
        return self.get_model(self.selected_model)

    def set_selected_model(self, model_name: str):
        self.selected_model = model_name

    def add_model(self, model_name: str, model: HARModel):
        self.models[model_name] = model

    def get_predictions(self) -> list[(float, float, np.ndarray)]:
        return self.predictions

    def clear_predictions(self):
        self.predictions = []

    def get_classes(self) -> list[str]:
        return self.classes

    def update_predictions(self, csi: CSI):
        model = self.get_selected_model()
        if not model:
            return
        
        amp = csi.get_amp()
        ts = csi.get_ts()

        # If no data or no new data, skip prediction
        if amp.shape[0] == 0 or self.last_prediction == ts[-1]:
            return

        self.last_prediction = ts[-1]
        ts_from, ts_to, confidence_scores = model.evaluate(amp, ts)
        self.predictions.append((ts_from, ts_to, confidence_scores))
        print(f"Model {model.get_name()} evaluated at {ts_from} - {ts_to} with scores: {confidence_scores}")

        # Remove old predictions
        self.predictions = [p for p in self.predictions if p[1] > ts[0]]
