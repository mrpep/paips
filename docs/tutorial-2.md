##### Understanding the outputs

Once we run the previous example, things like these are logged and showed in the terminal:

```
2021-04-12 15:46:39,269 — Paips — INFO — Gathering tasks for MainTask
2021-04-12 15:46:39,273 — Paips — INFO — MainTask: Hash 18e506c00658d80f884742ca8e57d8558a926444
2021-04-12 15:46:39,274 — Paips — INFO — MainTask: Running
2021-04-12 15:46:39,274 — Paips — INFO — ReadCSV: Hash 1a6c275b4cd933f9a1915eca07dce534df5e32e4
2021-04-12 15:46:39,275 — Paips — INFO — ReadCSV: Running
2021-04-12 15:46:39,951 — Paips — INFO — ReadCSV: Saving outputs
2021-04-12 15:46:39,960 — Paips — INFO — TrainValTestPartition: Hash e5728bea9009ec8d42140efd3b871f589d061119
2021-04-12 15:46:39,960 — Paips — INFO — TrainValTestPartition: Running
2021-04-12 15:46:39,965 — Paips — INFO — TrainValTestPartition: Saving outputs
2021-04-12 15:46:39,971 — Paips — INFO — MainTask: Saving outputs
```

So, we have the time when each task was executed, a unique hash to identify each task, and messages about each task being ran or its output saved.
Some questions arise: Why are all tasks saving outputs? Can we avoid it? Where are those outputs saved?

By default, the output of each task is serialized using **joblib** and saved in the <cache_folder>/<task_hash> directory.

Let's do a little experiment and run again:

```paiprun configs/ex1.yaml```

Now, this gets printed:

```
2021-04-12 15:53:02,691 — Paips — INFO — Gathering tasks for MainTask
2021-04-12 15:53:02,695 — Paips — INFO — MainTask: Hash f5c79c0e8e5111399b63a43deb2cbf44ba816a73
2021-04-12 15:53:02,696 — Paips — INFO — MainTask: Running
2021-04-12 15:53:02,696 — Paips — INFO — ReadCSV: Hash 1a6c275b4cd933f9a1915eca07dce534df5e32e4
2021-04-12 15:53:02,697 — Paips — INFO — ReadCSV: Caching
2021-04-12 15:53:02,714 — Paips — INFO — TrainValTestPartition: Hash e5728bea9009ec8d42140efd3b871f589d061119
2021-04-12 15:53:02,715 — Paips — INFO — TrainValTestPartition: Caching
2021-04-12 15:53:02,718 — Paips — INFO — MainTask: Saving outputs
```

Now, ReadCSV and TrainValTestPartition are not 'Running' nor 'Saving outputs'. Welcome to the world of **Cache**

This is what is happening under the hood. Before running the **process()** method of each task, a hash is generated from all the task parameters. Then, before running **process()**, we take a look inside the **cache** folder and see if <cache_folder>/<task_hash> exists. If it exists, instead of running again **process()**, we just load the saved outputs. This is really useful when a task takes a very long time and we don't want to run it again and again. However, some times we might want to regenerate the outputs and avoid caching. In that case, we can deactivate caching for a particular task adding the parameter:

```yaml
cache: False
```

or we can deactivate caching for all tasks adding the following argument when calling paiprun:

```
paiprun configs/ex1.yaml --no-caching
```

In those cases, the **process()** method is called regardless of if <cache_folder>/<task_hash> exists or not. If it exists, it will be replaced by the new outputs.



