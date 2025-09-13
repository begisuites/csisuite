import os
import numpy as np
from scipy.signal import resample
from models.model_base import HARModel
from services.api import Api
import joblib
import torch

PAD_LEN = 400

DEVICE = "cpu" 
if torch.cuda.is_available():
    DEVICE = "cuda"
elif torch.backends.mps.is_available():
    DEVICE = "mps"

class Normalize:
    def __init__(self, scaler):
        self.scaler = scaler

    def __call__(self, x):
        original_shape = x.shape
        x = x.reshape(-1, np.prod(x.shape[1:]))
        x = self.scaler.transform(x)
        x = x.reshape(original_shape)
        x = np.tanh(x)
        return x
    
class LSTMM(torch.nn.Module):
    def __init__(self, x_shape, y_shape, hidden_size=512, pool_kernel=10, num_layers=1):
        super(LSTMM, self).__init__()
        
        dim_input = x_shape[-1]
        dim_output = y_shape[-1]
        
        self.dim_input = dim_input

        self.pool_kernel = pool_kernel
        self.layer_norm = torch.nn.BatchNorm1d(dim_input)
        self.layer_pooling = torch.nn.AvgPool1d(pool_kernel, pool_kernel)
        self.layer_lstm = torch.nn.LSTM(input_size = dim_input, 
                                        hidden_size = hidden_size, 
                                        batch_first = True, 
                                        dropout = 0.3 if num_layers > 1 else 0, 
                                        num_layers = num_layers)
        self.layer_linear_1 = torch.nn.Linear(hidden_size, dim_output)
        self.dropout = torch.nn.Dropout(0.3)
        self.relu = torch.nn.ReLU()

    def forward(self, x):
        x = x.view(x.size(0), -1, self.dim_input)
        x = torch.permute(x, (0, 2, 1))
        x = self.layer_norm(x)
        x = self.layer_pooling(x) if self.pool_kernel > 1 else x
        x = torch.permute(x, (0, 2, 1))
        x, _ = self.layer_lstm(x)
        x = x[:, -1, :]
        x = self.dropout(x)
        x = self.layer_linear_1(x)
        return x

class LSTM(HARModel):
    def __init__(self, api: Api, num_classes: int):
        super().__init__(num_classes)
        self.api = api

        current_dir = os.path.dirname(__file__)
        self.normalizer = Normalize(joblib.load(os.path.join(current_dir, 'scaler.joblib')))

        self.model = LSTMM(torch.Size([PAD_LEN, 256]), torch.Size([5]), hidden_size=512, pool_kernel=20, num_layers=1).to(DEVICE)
        self.model.load_state_dict(torch.load(os.path.join(current_dir, 'har_ort_lstm.pth'), map_location=DEVICE))

    def evaluate(self, amp, ts) -> tuple[float, np.ndarray]:
        ts_to = ts[-1]
        ts_from_idx = np.searchsorted(np.array(ts), ts_to - 3.0)

        window_amp = amp[ts_from_idx:]
        window_amp = resample(window_amp, PAD_LEN, axis=0)
        window_amp = self.normalizer(window_amp)
        window_amp = torch.from_numpy(window_amp).float().unsqueeze(0).to(DEVICE)  

        self.model.eval()
        with torch.no_grad():
            output = self.model(window_amp).squeeze()
            confidence = torch.nn.functional.softmax(output, dim=0).cpu().numpy()

        return ts[ts_from_idx], ts_to, confidence
