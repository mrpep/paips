from paips.core import Task
import pandas as pd
from IPython import embed

class CSVToDataframe(Task):
    def process(self):
        path = self.parameters.get('path',None)
        delimiter = self.parameters.get('delimiter',',')
        return pd.read_csv(path,delimiter=delimiter)

class RandomSplit(Task):
    def process(self):
        data = self.parameters.get('in',None)
        splits = self.parameters.get('splits',None)
        idxs = data.index
        splits = {k: int(v*len(idxs)) for k,v in splits.items()}
        self.output_names = []
        outs = []
        for k, (s_name, s_n) in enumerate(splits.items()):
            self.output_names.append(s_name)
            df_remaining = data.loc[idxs]
            if k != len(splits) - 1:
                df_i = df_remaining.sample(n=s_n)
                outs.append(df_i)
                idxs = set(idxs) - set(df_i.index)
            else:
                outs.append(df_remaining)
        return tuple(outs)



