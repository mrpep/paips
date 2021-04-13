### Composing configuration files

There are 2 different ways to combine several configuration files into a single monster one. The first one is using the **!yaml** tag

##### !yaml tag

Let's suppose that we want to specify the random forest parameters in a separate configuration file like:

samples/configs/rf_hyperparameters.yaml

```yaml
n_estimators: !var n_estimators
criterion: !var criterion
max_depth: !var max_depth
max_features: !var max_features
```

In this case, it might not make a lot of sense to do this separation, but imagine that your model is a deep neural network instead. In that case, the configuration file
telling the architecture, loss functions, callbacks, metrics, optimizer, etc... might be a large one and it would be a good idea to separate it in a different file.
Now, the RandomForestRegressor task will look like:

samples/configs/ex4.yaml
```yaml
  RandomForestRegressor:
    class: RandomForestRegressor
    in: TrainValTestPartition->train
    target_col: quality
    features_col: null
    parameters: !yaml configs/rf_hyperparameters.yaml
```

So, what the **!yaml** tag does is to open the config path and insert it into the corresponding key. 
Take into account that the yaml path must be specified using an absolute path, or a path relative to the current working directory.

Now, suppose that you want to be able to easily change the model by another one, like a Gradient Boosting Machine. 
Instead of writing a completely new config, another idea is to have several configs that contain the specification of different models, and then being able to integrate them to the pipeline.
To do it, paips has **includes**.

##### Includes

Let's understand it by example. Now, we want to be able to easily switch between different tasks corresponding to different models. We will switch between the random forest and the gradient boosting machine.

First, let's define a task to train gradient boosting machines, which again will be based on scikit-learn:

samples/tasks/\__init__.py
```python
class GradientBoostingMachineRegressor(Task):
    def process(self):
        data = self.parameters.get('in')
        target_col = self.parameters.get('target_col',None)
        features_col = self.parameters.get('features_col',None)
        kwargs = self.parameters.get('parameters',None)

        if features_col is None:
            features_col = list(set(data.columns) - set([target_col]))

        targets = np.array(data[target_col])
        features = np.array(data[features_col])

        gb_model = gbmr(**kwargs)
        gb_model.fit(features, targets)

        return gb_model
```

Now, let's write a configuration file for each of the models:

samples/configs/rf_config.yaml

```yaml
defaults:
  n_estimators: 100
  criterion: mse
  max_depth: null
  max_features: auto
RegressorModel:
  class: RandomForestRegressor
  in: (in_task)->train
  target_col: quality
  features_col: null
  parameters: !yaml configs/rf_hyperparameters.yaml
```

samples/configs/gbm_config.yaml

```yaml
defaults:
  loss: ls
  learning_rate: 0.1
  n_estimators: 100
  criterion: friedman_mse
  max_depth: 3
  max_features: null
RegressorModel:
  class: GradientBoostingMachineRegressor
  in: (in_task)->train
  target_col: quality
  features_col: null
  parameters:
    loss: !var loss
    learning_rate: !var learning_rate
    n_estimators: !var n_estimators
    criterion: !var criterion
    max_depth: !var max_depth
    max_features: !var max_features
```

Then, the main config will be:

samples/configs/ex5.yaml
```yaml
modules:
- tasks
global:
  model: random_forest
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
  include:
    switch: !var model
    configs:
    - name: random_forest
      config: rf_model.yaml
      in_task: TrainValTestPartition
    - name: gbm
      config: gbm_model.yaml
      in_task: TrainValTestPartition
  RegressorPredictVal:
    class: SklearnModelPredict
    in: TrainValTestPartition->validation
    target_col: quality
    features_col: null
    model: RegressorModel->out
  MSEVal:
    class: MeanSquaredError
    y_pred: RegressorPredictVal->predictions
    y_true: RegressorPredictVal->targets
    export: True
 ```
 
 Let's dissect all of this. First of all, in the main configuration file we use the **include** key. It has a **switch** key, whose value is the variable model. That variable is defined in **global** and its value is 'random_forest'. So, when the configuration file is parsed, switch will have a value of 'random_forest'. Then we have a **configs** key, which is a list of configuration files. Each of the configuration files has a name and a configuration file path (which will be relative to the includer configuration file path). The first one is random_forest, and as switch is also random_forest, that will be the included config. If instead, switch values 'gbm', then gbm_model.yaml would get included.
 
Then, each configuration in the list can have other parameters, like in_task in this case. If you take a look at gbm_config.yaml and rf_config.yaml you will see that the parameter 'in' has a value of '(in_task)->train'. When the configuration file gets included, (in_task) will be replaced by the value of in_task, which in this case is 'TrainValTestPartition'. Enclosing between parentheses is a way of telling the parser to replace it when doing the include.

Finally, each of the configuration files has a **defaults** key, which tells the parser to replace all !var tags by the values in **defaults** if those variables are not defined in **global**.

With these composition tools we have a lot of flexibility to reuse configuration files in different contexts, and changing many aspects of a pipeline using minimal modifiers in the command line. For example, in this example we now can do a lot of things:

```
paiprun configs/ex5.yaml
```

will run the default pipeline which is a random forest regressor.

```
paiprun configs/ex5.yaml --mods "global/model=gbm"
```

will run the same pipeline, but change the random forest by a gradient boosting machine, using its default values.

```
paiprun configs/ex5.yaml --mods "global/model=gbm&global/learning_rate=0.05"
```

will also change the learning rate to 0.05

and so on... options are infinite.
Also, we could easily add new models to explore by adding new configs to the include key and writing the corresponding tasks.

In the next [section](tutorial-5.md), we will take a look at some advanced functionalities like using nested pipelines, applying maps and doing lazy execution.
