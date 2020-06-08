from core import Task
import glob
from IPython import embed
from pathlib import Path
from pymediainfo import MediaInfo
import tqdm
import pandas as pd

class Split(Task):
	def process(self):
		data = self.parameters['in']
		split_col = self.parameters['split_col']
		partition_names = data[split_col].unique()
		self.output_names = partition_names

		return tuple([data[data[split_col] == part_name] for part_name in partition_names])
