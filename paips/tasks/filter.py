from paips import Task
import pandas as pd
from pathlib import Path
from IPython import embed

class Filter(Task):
    def __init__(self,config,global_config):
        super().__init__(config,global_config)
        self.list_path = self.config['list_path']
        self.list_file = self.config['list_file']

        if not isinstance(self.list_file,list):
            self.list_file = [self.list_file]

        self.inputs=self.config.get('inputs',['in'])
        self.outputs=self.config.get('outputs',['out'])

        self.required_kwargs=[]

    def operation(self,data):
        ix_valids = []
        for flist in self.list_file:
            ix_valids.append(set([l.strip() for l in open(str(Path(self.list_path,flist).absolute()))]))

        ix_valid = list(set.intersection(*ix_valids))
        df_list = [df.loc[df.index[df.index.isin(ix_valid)]] for df in data]

        return df_list