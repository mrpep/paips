##### Hyperparameter exploration example

We will keep working in the machine learning pipeline we built. Now that we have partitioned the data, we want to actually train something. You will need to have [scikit-learn](https://scikit-learn.org/stable/) installed in your system.
Let's train a random forest classifier. We extend the samples/configs/ex1.yaml config:

samples/configs/ex2.yaml
```yaml
modules:
- tasks
Tasks:
  ReadCSV:
    class: CSVToDataframe
    path: https://archive.ics.uci.edu/ml/machine-learning-databases/wine-quality/winequality-red.csv
    delimiter: ;
  TrainValTestPartition:
    class: RandomSplit
    in: ReadCSV->out
    splits:
      train: 0.7
      validation: 0.1
      test: 0.2
  RandomForestRegressor:
    class: RandomForestRegressor
    in: TrainValTestPartition->train
    target_col: quality
    features_col: null
    parameters:
      n_estimators: 100
      criterion: mse
      max_depth: null
      max_features: auto
```

So the first step would be to code RandomForestRegressor task by wrapping **sklearn.ensemble.RandomForestRegressor**. We use a regressor because the dataset we are working on has a continous target (wine quality rated from 0 to 10).

samples/tasks/\_\_init_\_.py
```python
class RandomForestRegressor(Task):
    def process(self):
        from sklearn.ensemble import RandomForestRegressor as rfr
        import numpy as np

        data = self.parameters.get('in')
        target_col = self.parameters.get('target_col',None)
        features_col = self.parameters.get('features_col',None)
        kwargs = self.parameters.get('parameters',None)

        if features_col is None:
            features_col = list(set(data.columns) - set(target_col))

        targets = np.array(data[target_col])
        features = np.array(data[features_col])

        rf_model = rfr(**kwargs)
        rf_model.fit(features, targets)

        return rf_model
```


