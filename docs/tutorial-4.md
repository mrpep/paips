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
Instead of writing a completely new config, another idea is to have several configs that contain the specification of a different model, and then being able to integrate it to the pipeline.
To do it, paips has **includes**. Let's look at an example:


