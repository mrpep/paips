##### Hyperparameter exploration example

We will keep working in the machine learning pipeline we built. Now that we have partitioned the data, we want to actually train something.
Let's train a random forest classifier using scikit-learn. We extend the samples/configs/ex1.yaml config:

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

samples/tasks/__init__.py
```python

```

