from core import Task
import tqdm
import pandas as pd
from IPython import embed
import numpy as np
from deytah.batch_generator import BatchGenerator

class DeytahGenerator(Task):
    def process(self):
        stratified_batch = self.parameters.get('stratified_batch',False)
        batchgen = BatchGenerator(
            data=self.parameters['in'],
            input_names=self.parameters['deytah_x'], 
            output_names=self.parameters['deytah_y'],
            data_processor_config=self.parameters['deytah_config'],
            batch_size=self.parameters['batch_size'],
            stratified=stratified_batch, 
            default_processors=self.parameters.get('default_processors',True)
        )

        return batchgen

        