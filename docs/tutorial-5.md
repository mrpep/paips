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
```


