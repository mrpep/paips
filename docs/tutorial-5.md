##### Doing K-Fold Cross Validation

Now,we are going to extend the ML pipeline we have been building and evaluate our model using 5-fold cross validation.
K-Fold cross validation consists of dividing our dataset into 5 non-overlapping sets or folds. Then, our model is trained in 4 of those folds and evaluated in the remaining fold. This is repeated until all folds are evaluated, so in this example, 5 models are trained. Then, the predictions for each of the 5 folds are merged and metrics are calculated over those merged predictions. Another option is to calculate metrics for each fold and then reporting the average metric over the 5 folds.

In terms of pipelines, we need to apply a part of our pipeline 5 times over different inputs (the different folds). How can we do this in an efficient way?
The answer is **Nested Pipelines**

##### Nested Pipelines

The task that always runs behind paips is **TaskGraph**. It receives a parameter Tasks, which is a dictionary with a lot of tasks. Then, analyzes the dependencies and creates a directed acyclic graph where each node is a task. Finally, the graph is topologically sorted and an order of execution for the tasks is determined. Then, each task is executed in the right order so that when a task B needs data from a task A, task A runs first.

To solve our 5-Fold cross validation problem, we are going to think of what is done for each fold as a new pipeline inside the bigger one.
This pipeline will receive training and evaluation folds, will train the model in the training folds and do predictions on the evaluation folds.

Let's see the final configuration file and then analyze it:

samples/configs/ex6.yaml

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
  RandomFolds:
    class: KFoldGenerator
    in: ReadCSV->out
    folds: 5
  FoldPipeline:
    class: TaskGraph
    in:
      train: !map RandomFolds->train
      validation: !map RandomFolds->validation
    outputs:
      predictions: RegressorPredictFold->predictions
      targets: RegressorPredictFold->targets
    Tasks:
      include:
        switch: !var model
        configs:
        - name: random_forest
          config: rf_model.yaml
          in_task: self
        - name: gbm
          config: gbm_model.yaml
          in_task: self
      RegressorPredictFold:
        class: SklearnModelPredict
        in: self->validation
        target_col: quality
        features_col: null
        model: RegressorModel->out
  ConcatenatePredictions:
    class: Concatenate
    in: FoldPipeline->predictions
  ConcatenateTargets:
    class: Concatenate
    in: FoldPipeline->targets
  MSEVal:
    class: MeanSquaredError
    y_pred: ConcatenatePredictions->out
    y_true: ConcatenateTargets->out
    export: True
```

The first task, ReadCSV is the same as before. Then, we have RandomFolds, which is from a new class KFoldGenerator:

```python
class KFoldGenerator(Task):
    def process(self):
        data = self.parameters['in']
        n_folds = self.parameters['folds']
        idxs = data.index
        samples_per_fold = len(idxs)//n_folds

        assigned_idxs = []
        val_folds = []

        for i in range(n_folds):
            if i < n_folds - 1:
                df_i = data.loc[~idxs.isin(assigned_idxs)]
                df_i = df_i.sample(n=samples_per_fold)
                assigned_idxs.extend(df_i.index)
            else:
                df_i = data.loc[~idxs.isin(assigned_idxs)]
            val_folds.append(df_i)
        
        train_folds = [pd.concat(val_folds[:i] + val_folds[i+1:]) for i in range(n_folds)]
        self.output_names = ['train','validation']
        
        return train_folds, val_folds
```

This task, basically takes as input the dataset dataframe, and returns all the training and validation folds. These outputs are lists with 5 different dataframes, each with training/validation dataframes for each fold.

Then, we have FoldPipeline, which is the pipeline inside the pipeline. It takes inputs as any other task. These inputs are the training and validation dataframes, but there is a yaml tag **!map**. This makes the whole task to be applied to each of the elements of that input. So, in this case the inputs are lists of 5 dataframes. When using !map, the task, which is a pipeline, is applied to each of the dataframes. 

Then, the pipeline has outputs, which are outputs of tasks inside the pipeline. Basically, the task will export those outputs from the whole pipeline. In this case, we want to know what was predicted and what were the ground truth values for each fold. These two outputs will allow us to calculate metrics.

The pipeline has Tasks, as our main pipeline. This pipeline trains the model and makes predictions as before. Notice the use of **self** to reference the elements that are input to the pipeline itself.

Once the FoldPipeline is executed 5 times, it will generate 5 outputs (a list of 5 predictions, and a list of 5 targets). So, we need to combine the 5 outputs to get predictions and targets for the full dataset. We create a very simple task Concatenate which does the work:

```python
class Concatenate(Task):
    def process(self):
        data = self.parameters['in']
        return np.concatenate(data)
```

Then, the MSEVal task will receive 2 arrays with all the predictions and targets merged. And that's all about nested pipelines.

##### Lazy execution

Sometimes, you might want a task to not execute, but instead to be returned as a task to then be executed at another point of the pipeline.
One example is when training a neural network and doing data augmentation. In that case, you might have a generator, which loads a batch of data from disk to memory (for example, images). Then does some normalization, creates new images by rotating them, adding noise, blurring, etc... And finally, the resulting tensor is fed to the neural network. A nice thing about paips is that you can do all of this easily:

1) First create a TaskGraph task (a nested pipeline), which has all the mentioned tasks (tasks that load images, rotates them, blurs them, etc...). We will call it DataGeneratorPipeline.
2) Then, add to that task the parameter:

```yaml return_as_class: True```

This will make the DataGeneratorPipeline to run in lazy mode. So the output of the task will be the task itself.
3) Then, create a Generator task, which will do all the common stuff (receive a batch_size parameter, a dataframe with the training data or metadata, etc...), and make it accept the DataGeneratorPipeline task as a parameter. For example:

```yaml batch_process_task: DataGeneratorPipeline->out```

4) Finally, in the function called by the Generator at each training step, the batch_process_task task (in this case DataGeneratorPipeline), will get executed by calling its **process()** method.

A full example can be seen at https://github.com/habla-liaa/ser-with-w2v2


