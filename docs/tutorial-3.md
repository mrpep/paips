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
  RandomForestPredictVal:
    class: SklearnModelPredict
    in: TrainValTestPartition->validation
    target_col: quality
    features_col: null
    model: RandomForestRegressor->out
  MSEVal:
    class: MeanSquaredError
    y_pred: RandomForestPredictVal->predictions
    y_true: RandomForestPredictVal->targets
    export: True
```

So, now we have a RandomForestRegressor which trains the random forest model, RandomForestPredictVal which takes the validation data and makes predictions over it and also returns the ground truth values, and MSEVal which calculates the mean squared error between the predicted values and the ground truth in the validation set.

The new tasks are coded in a same fashion as we did previously:

samples/tasks/\_\_init_\_.py
```python
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
```

So, finally we run the complete pipeline:

```
paiprun configs/ex2.yaml --output_path "my_experiments/rf_regressor"
```

Now, imagine that you want to use 300 trees instead of 100. It would be a bit ugly to copy the whole configuration file and just change the n_estimators parameter. We have a solution: using **Modifiers**.

```
paiprun configs/ex2.yaml --output_path "my_experiments/rf_regressor_300trees" --mods "Tasks/RandomForestRegressor/parameters/n_estimators=300"
```

If you want to modify more than one parameter at the same time, no problem:
```
paiprun configs/ex2.yaml --output_path "my_experiments/rf_regressor_300trees_depth20" --mods "Tasks/RandomForestRegressor/parameters/n_estimators=300&Tasks/RandomForestRegressor/parameters/max_depth=20"
```

Modifiers are very powerful, but sometimes paths to a parameter can become very long or hard to write. In that case, it is a better idea to use **Variables**

Let's reformulate our configuration file:

configs/ex3.yaml

```yaml
modules:
- tasks
global:
  n_estimators: 100
  criterion: mse
  max_depth: null
  max_features: auto
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
      n_estimators: !var n_estimators
      criterion: !var criterion
      max_depth: !var max_depth
      max_features: !var max_features
  RandomForestPredictVal:
    class: SklearnModelPredict
    in: TrainValTestPartition->validation
    target_col: quality
    features_col: null
    model: RandomForestRegressor->out
  MSEVal:
    class: MeanSquaredError
    y_pred: RandomForestPredictVal->predictions
    y_true: RandomForestPredictVal->targets
    export: True
```




