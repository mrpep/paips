from core import Task
import tqdm
import pandas as pd
from IPython import embed
import numpy as np
from deytah.batch_generator import BatchGenerator
from dienen import Model
import kahnfigh

class DienenModel(Task):
    def process(self):
        dienen_model = Model(self.parameters['dienen_config'])
        keras_model = dienen_model.build()
        dienen_model.fit(self.parameters['generator'])