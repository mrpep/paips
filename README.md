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
First of all, we are going to code each of the pipeline blocks, which are the tasks that are going to be executed. We will create a python module 'tasks'.
In the __init__.py we will write the different needed tasks:

- First we need to read a csv. We will create a task that turns a csv into a pandas DataFrame:

tasks/__init__.py
```python
from paips.core import Task
import pandas as pd

class CSVToDataframe(Task):
    def process(self):
        path = self.parameters.get('path',None)
        delimiter = self.parameters.get('delimiter',',')
        return pd.read_csv(path,delimiter=delimiter)
```

- We will also create a task to randomly split a dataframe into parts with a given proportion. This will allow us to split our dataset into training, validation and test sets:






