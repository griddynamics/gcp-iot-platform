import os
import json
import torch
from typing import Sequence, Tuple
from torch import nn
from models import LinearModel

class Predictor(nn.Module):

    def __init__(self, model_dir: str) -> None:
        super(Predictor, self).__init__()
        cfg_file = os.path.join(model_dir, 'config.json')
        mdl_file = os.path.join(model_dir, 'pytorch_model.bin')
        if not os.path.isfile(cfg_file):
            raise RuntimeError("Missing the config.json file")
        if not os.path.isfile(mdl_file):
            raise RuntimeError("Missing the pytorch_model.bin file")

        with open(cfg_file) as f:
            self.config = json.load(f)
        checkpoint = torch.load(mdl_file)
        self.model = LinearModel(self.config['input_size'])
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.bounds = self.config['bounds']
        self._mean = self.config['mean']
        self._std = self.config['std']
    
    def forward(self, x: Sequence) -> Tuple:
        output = self.model(x.float())
        return output
