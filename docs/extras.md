Sometimes we need to force a task to run first of all. We can do it by passing the parameter:

```yaml
run_first: True
```

Also, sometimes we want a task B to be executed after task A, independently of if task B received data from task A. In that case, we can invent a dummy parameter
which takes task A output:

```yaml
run_after: TaskA->out
```

Sometimes, there might be more than one task that can be executed at any time. Maybe we want in that case that a task runs first than others, because we want to get those results earlier. In that case we can add a priorize parameter:

```yaml
priorize: True
```
