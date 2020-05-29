from paips import Task
from IPython import embed
import utils
from pathlib import Path
import networkx as nx

class TaskGraph(Task):
	def __init__(self, config):
		super().__init__(config)
		self.required_fields = ['Tasks']
		self.check_requirements()
		self.inputs = ['in']
		self.graph = nx.DiGraph()
		self.load_modules()
		self.gather_tasks()
		self.connect_tasks()
		self.get_dependency_order()
		self.tasks_io = {}

	def gather_tasks(self):
		#Here, all the tasks in config are instantiated and added as nodes to a nx graph
		self.task_nodes = {}
		for task_name, task_config in self.config['Tasks'].items():
			task_class = task_config['class']
			task_obj = [getattr(module,task_class) for module in self.task_modules if task_class in utils.get_classes_in_module(module)]
			if len(task_obj) == 0:
				raise Exception('{} not recognized as a task'.format(task_class))
			elif len(task_obj) > 1:
				raise Exception('{} found in multiple task modules. Rename the task in your module to avoid name collisions'.format(task_class))
			task_obj = task_obj[0]
			task_instance = task_obj(task_config)
			task_instance.set_name(task_name)
			self.task_nodes[task_name] = task_instance
			self.graph.add_node(task_instance)

	def connect_tasks(self):
		#Here, edges are created using the dependencies variable from each task
		for task_name, task in self.task_nodes.items():
			dependencies = task.get_dependencies()
			if len(dependencies)>0:
				for dependency in dependencies:
					self.graph.add_edge(self.task_nodes[dependency],task)

	def load_modules(self):
		module_paths = ['core_tasks.py']
		if 'modules' in self.config:
			module_paths_ = self.config['modules']
			if not isinstance(module_paths,list):
				module_paths_ = [module_paths_]
			module_paths.extend(module_paths_)
		self.task_modules = []
		for module_path in module_paths:
			self.task_modules.append(utils.module_from_file(Path(module_path).stem,module_path))

	def get_dependency_order(self):
		self.dependency_order = list(nx.topological_sort(self.graph))

	def run(self):
		#Here, the execution is determined using BFS and all tasks are ran in the corresponding order
		print('{}: Running a bunch of tasks'.format(self.name))
		for task in self.dependency_order:
			embed()
			#output = task.run()
			#self.tasks_io.update(output)


