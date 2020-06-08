from core import Task
import tqdm
import pandas as pd
from IPython import embed
import numpy as np

class Framer(Task):
	def process(self):
		df_data = self.parameters['in']
		out_dfs = []
		for logid, row in tqdm.tqdm(df_data.iterrows()):
			max_time = float(row[self.parameters['time_column']])
			starts = np.arange(0,max_time-self.parameters['frame_size'],self.parameters['hop_size'],dtype=int)
			ends = starts + self.parameters['frame_size']
			new_ids = ['{}_{}'.format(logid,i) for i in range(len(starts))]
			row_dict = {'start': starts,
						'end': ends,
						'logid': new_ids}
			for k,v in row.iteritems():
				row_dict[k] = v
			df_i = pd.DataFrame(row_dict).set_index('logid')
			out_dfs.append(df_i)

		return pd.concat(out_dfs)