from paips.core import Task
import pandas as pd
from sklearn.ensemble import RandomForestRegressor as rfr
import numpy as np
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

class RandomForestRegressor(Task):
    def process(self):
        data = self.parameters.get('in')
        target_col = self.parameters.get('target_col',None)
        features_col = self.parameters.get('features_col',None)
        kwargs = self.parameters.get('parameters',None)

        if features_col is None:
            features_col = list(set(data.columns) - set([target_col]))

        targets = np.array(data[target_col])
        features = np.array(data[features_col])

        rf_model = rfr(**kwargs)
        rf_model.fit(features, targets)

        return rf_model

class SklearnModelPredict(Task):
    def process(self):
        data = self.parameters.get('in',None)
        target_col = self.parameters.get('target_col',None)
        features_col = self.parameters.get('features_col',None)
        model = self.parameters.get('model',None)

        if features_col is None:
            features_col = list(set(data.columns) - set([target_col]))

        predictions = model.predict(np.array(data[features_col]))
        targets = np.array(data[target_col])
        self.output_names = ['predictions','targets']

        return predictions,targets

class MeanSquaredError(Task):
    def process(self):
        from sklearn.metrics import mean_squared_error

        predictions = self.parameters.get('y_pred', None)
        targets = self.parameters.get('y_true', None)

        return mean_squared_error(targets,predictions)




