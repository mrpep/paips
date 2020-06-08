from paips import Task
import pandas as pd
from pathlib import Path
from IPython import embed

class Filter(Task):
    def __init__(self,config,global_config):
        super().__init__(config,global_config)
        self.list_path = self.config.get('list_path',None)
        self.list_file = self.config.get('list_file',None)

        self.values = self.config.get('values',None)
        self.behaviour = self.config.get('behaviour','keep')

        if self.list_file and not isinstance(self.list_file,list):
            self.list_file = [self.list_file]

        self.inputs=self.config.get('inputs',['in'])
        self.outputs=self.config.get('outputs',['out'])
        self.axis=self.config.get('axis','row')

        self.required_kwargs=[]

    def operation(self,data):
        ix_valids = []
        if self.list_file:
            for flist in self.list_file:
                ix_valids.append(set([l.strip() for l in open(str(Path(self.list_path,flist).absolute()))]))

            ix_valids = list(set.intersection(*ix_valids))

        if self.values:
            ix_valids.extend(self.values)
        
        if self.behaviour == 'ignore':
            ix_valids = [ix for ix in data.index if ix not in ix_valids]

        if self.axis == 'row':
            df_list = [df.loc[df.index[df.index.isin(ix_valids)]] for df in data]
        elif self.axis == 'col':
            df_list = [df[df.columns[df.column.isin(ix_valids)]] for df in data]
        else:
            raise Exception('Invalid value {} for parameter axis. Allowed values: row, col'.format(self.axis))
            
        return df_list