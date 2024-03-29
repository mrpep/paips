##### Building a machine learning pipeline

We are going to build a minimalistic machine learning pipeline.
Let's take a look at the configuration file:

samples/configs/ex1.yaml

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
    export: True
```
Let's break it into parts:
First of all, there is a **modules** key. This consists of a list of python modules with tasks. So, in this case, we have a module called tasks which will contain the different tasks that we are going to use in the pipeline. 

Then, we have the **Tasks** key. It contains all the tasks that are going to be executed. In this configuration file there are 2 tasks which will be executed: ReadCSV and TrainValTestPartition. 

Notice that both tasks have a **class** key, which tells paips, which class from the modules the task corresponds to. So in this case, the ReadCSV task will instantiate a CSVToDataframe task. 

We have other keys in the ReadCSV task: path and delimiter. These are **parameters** and will be accessible from inside each class through the parameters dictionary (more on that later...). In this case, ReadCSV will read a csv file and we have to indicate the path of the file, and in this case, as the delimiter is a semicolon, we tell it through the delimiter parameter.

Now, let's take a look at the TrainValTestPartition task. It has some new features:
- the in parameter has a value ReadCSV->out. The **-> symbol** is a very important one. It is used to reference other tasks. In this case, we are telling paips that the in parameter will take the output of the ReadCSV task. By default, task outputs are called out, but we could use other names (more on that later...)
- **export** is an special parameter which indicates that the output of this task will be saved in the output path, in a nice and clear way.

Then, splits is a parameter, which in this case will indicate the names of the different splits, and the proportions. We will split the dataset into a train, validation and test sets, with proportions of 70, 10 and 20% respectively.

Now that we defined the configuration file, it is time to actually write Python code which executes the tasks. We will create the python module 'tasks'.
In the __init__.py we will write the different needed tasks:

tasks/\__init__.py
```python
from paips.core import Task
import pandas as pd

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
        self.output_names = sorted([k for k in splits])
        outs = []
        for k,split_name in enumerate(self.output_names):
            df_remaining = data.loc[idxs]
            if k != len(splits) - 1:
                df_i = df_remaining.sample(n=splits[split_name])
                outs.append(df_i)
                idxs = set(idxs) - set(df_i.index)
            else:
                outs.append(df_remaining)
        return tuple(outs)
```

So in the first line we import the class Task from paips. This is the class all tasks inherit from. We also import pandas, so make sure that it is installed in your system if you want to try this example.

Then we create our task CSVToDataframe. When we write our own tasks, we have to define the method **process()**, which will be executed when the task is ran. All tasks have a member called **parameters**, a dictionary which contains all parameters defined in the configuration file. We use the .get() method to access the different dictionary keys. Finally, the dataframe is returned using the pandas read_csv() function.

Now, let's take a look at RandomSplit. The template is similar: it inherits from Task, and overrides the process() method. The parameters are read from self.parameters, and then there is some code to do the splitting. But, in this case there is a new concept to be introduced, which we will call **dynamic outputs**.

If you take a close look at the code, you will notice that the task will return 3 outputs in this case, instead of 1 like the CSVToDataframe task. Moreover, if the configuration file is changed, and another split is added, it will return 4 outputs. So, the number of outputs depends of the configuration file definition. Another important thing is that we will need to differentiate those 3 outputs. This is because, for example, we might need to access the train partition from another task. In that case we would do something like: in: TrainValTestPartition->train. Notice that in order to access ReadCSV output we did ReadCSV->out, but in this case we have more outputs: TrainValTestPartition->train, TrainValTestPartition->validation and TrainValTestPartition->test. That output differentiation is done in the code by overwriting the self.output_names list, which by default is ['out']. When the code is executed, the list has ['train', 'validation', 'test'] value. At the same time, the function returns the corresponding dataframes. So, when generating dynamic outputs make sure that the order of the names match the order of the outputs. Also, it is important to ensure that if we run the same code with the same parameters multiple times, outputs should always be the same. That is the reason why self.output_names is sorted, as keys in a dictionary do not have a fixed order.

Now, we have the 2 components of every paips pipeline: tasks and a configuration file. To run this example you can open a terminal and go to the samples folder. From there run:

```
paiprun configs/ex1.yaml
```

Let's understand the outputs in the next [tutorial](tutorial-2.md).
