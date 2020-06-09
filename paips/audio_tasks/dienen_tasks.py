from core import Task
import tqdm
import pandas as pd
from IPython import embed
import numpy as np
from deytah.batch_generator import BatchGenerator

class DienenModel(Task):
    def process(self):
        embed()