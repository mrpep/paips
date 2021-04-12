# Paips
Run complex Python pipelines from command line using configuration files.

### How it works
- First define tasks that you want to be executed. These tasks are written in Python and consist of classes inheriting from paips.Task. Tasks can receive parameters and data from other tasks, return data, and be interconnected.
- Then, write one or more configuration files, which will tell Paips which tasks to run, with which parameters and how they will be connected. Configuration files are written in yaml, are modular and can be easily composed and also modified from command line.
- Finally, run in command line:
```
paiprun <config_path>
```
and the tasks declared in the configuration file will be executed in the right order.

Now, hands on pipelining...

### Installation


### Tutorial

##### Building a machine learning pipeline

We are going to build a minimalistic machine learning pipeline.
Let's take a look at the configuration file:

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
First of all, we are going to code each of the pipeline blocks, which are the tasks that are going to be executed. We will create a python module 'tasks'.
In the __init__.py we will write the different needed tasks:

- First we need to read a csv. We will create a task that turns a csv into a pandas DataFrame:

tasks/\__init__.py
```python
from paips.core import Task
import pandas as pd

class CSVToDataframe(Task):
    def process(self):
        path = self.parameters.get('path',None)
        delimiter = self.parameters.get('delimiter',',')
        return pd.read_csv(path,delimiter=delimiter)
```

So in the first line we import the class Task from paips. This is the class all tasks inherit from. We also import pandas, so make sure that it is installed in your system if you want to try this example.

Then we create our task CSVToDataframe. When we write our own tasks, we have to define the method **process()**, which will be executed when the task is ran. All tasks have a member called **parameters**, a dictionary which contains all parameters defined in the configuration file. Finally, the dataframe is returned.

- We will also create a task to randomly split a dataframe into parts with a given proportion. This will allow us to split our dataset into training, validation and test sets:






