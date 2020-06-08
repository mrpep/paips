from core import Task
import tqdm
import pandas as pd
from IPython import embed
import numpy as np

class Zipper(Task):
	def __init__(self,parameters,global_parameters=None,name=None,logger=None):
		super().__init__(parameters,global_parameters,name,logger)

	def process(self):
		progbar = tqdm.tqdm(total=len(self.parameters['zip_by'])+1)
		zipped_df = self.parameters['in'].groupby(self.parameters['zip_by']).aggregate(lambda x: [x.tolist()])
		progbar.update(1)
		zipped_df = zipped_df.applymap(lambda x: x[0])
		cols = zipped_df.columns
		for i,level_name in enumerate(self.parameters['zip_by']):
			zipped_df[level_name] = zipped_df.index.get_level_values(i)
			zipped_df[level_name] = zipped_df.apply(lambda x: [x[level_name]]*len(x[cols[0]]),axis=1)
			progbar.update(1)
		progbar.close()
		
		zipped_df = zipped_df.reset_index(drop=True)
		return zipped_df


		 