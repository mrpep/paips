from core import Task
import tqdm
import pandas as pd
from IPython import embed
import numpy as np

class Zipper(Task):
	def process(self):
		progbar = tqdm.tqdm(total=len(self.parameters['zip_by'])+1)
		zipped_df = self.parameters['in'].groupby(self.parameters['zip_by']).aggregate(lambda x: [x.tolist()])
		progbar.update(1)
		zipped_df = zipped_df.applymap(lambda x: x[0])
		cols = zipped_df.columns
		columns_to_apply = self.parameters.get('columns',list(cols)+self.parameters['zip_by'])

		for i,level_name in enumerate(self.parameters['zip_by']):
			zipped_df[level_name] = zipped_df.index.get_level_values(i)
			if level_name in columns_to_apply:
				zipped_df[level_name] = zipped_df.apply(lambda x: [x[level_name]]*len(x[cols[0]]),axis=1)
			progbar.update(1)
		progbar.close()
		
		cols_not_affected = [col for col in cols if col not in columns_to_apply]
		zipped_df = zipped_df.reset_index(drop=True)

		zipped_df[cols_not_affected] = zipped_df[cols_not_affected].applymap(lambda x: x[0])
		
		return zipped_df


		 