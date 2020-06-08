import networkx as nx

def make_graph_from_tasks(task_nodes):
	graph = nx.DiGraph()
	for task_name, task in task_nodes.items():
		dependencies = task.search_dependencies()
		if len(dependencies)>0:
			for dependency in dependencies:
				graph.add_edge(task_nodes[dependency],task)

	return graph