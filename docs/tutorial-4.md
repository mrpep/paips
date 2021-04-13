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





