import os
import json
import logging
import torch
import numpy as np
import pandas as pd
from google.cloud.logging import Client as LClient
from ts.torch_handler.base_handler import BaseHandler
from predictor import Predictor


PROJECT = os.environ.get('PROJECT')

log_client = LClient(project=PROJECT)
logger = logging.getLogger(__name__)


class TimeSeriesHandler(BaseHandler):
    """
    The handler takes an input metrics history and returns the detectors prediction 
    alongside upper and lower boundaries of expected value.
    """
    def __init__(self):
        super(TimeSeriesHandler, self).__init__()
        self.initialized = False
        self.gcs = None

    def initialize(self, ctx):
        """Loads the model.pt file and initialized the model object.
        """
        self.manifest = ctx.manifest

        properties = ctx.system_properties
        model_dir = properties.get("model_dir")

        self.device = torch.device('cpu') # torch.device("cuda:" + str(properties.get("gpu_id")) if torch.cuda.is_available() else "cpu")
        # Load model
        self.model = Predictor(model_dir)
        self.model.to(self.device)
        self.model.eval()
        logger.debug('Model from path {0} loaded successfully'.format(model_dir))
        self.initialized = True

    def preprocess(self, data):
        """Preprocessing request data, normalizing input signal"""
        assert (
            data is not None
            and len(data) > 0 
            and (data[0].get("data") is not None 
                 or data[0].get("body") is not None)
        ), "There is no data to process!"
        dt = data[0].get("data")
        if dt is None:
            dt = data[0].get("body")
        logger.info("Received data: {}".format(data))

        data = json.loads(dt)
        inputs = pd.read_json(data['values'], lines=True).T
        inputs.columns = ['value']
        inputs['value'] = (inputs['value'] - self.model._mean) / self.model._std
        inputs.sort_index(inplace=True)
        inputs = inputs['value']
        return inputs.values

    def inference(self, inputs):
        """Predict the possible value for the current timestamp. Returns possible and real values
        """
        with torch.no_grad():
            prediction = self.model(torch.from_numpy(inputs[:self.model.config['input_size']].reshape((1,self.model.config['input_size'])))).cpu().squeeze().item()
        return [prediction, inputs[self.model.config['input_size']]]

    def postprocess(self, inference_output):
        """Adding upper and lower expected values to the inference output, denormalizing"""
        possible = inference_output[0] * self.model._std + self.model._mean
        real = inference_output[1] * self.model._std + self.model._mean
        lower_bound = possible + self.model.bounds[0] * self.model._std
        upper_bound = possible + self.model.bounds[1] * self.model._std
        if lower_bound > real:
            post_out = -1, possible, real, lower_bound, upper_bound
        elif upper_bound < real:
            post_out = 1, possible, real, lower_bound, upper_bound
        else:
            post_out = 0, possible, real, lower_bound, upper_bound
        return [post_out]
