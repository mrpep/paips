from paips import Task
from IPython import embed
import utils
from pathlib import Path
import networkx as nx
from operator import itemgetter

class TaskGraph(Task):
	def __init__(self, config, global_config):
		"""
		TaskGraph represents a task which consists of multiple subtasks to be executed, potentially depending each of these tasks
		of previously executed tasks. It will generate a graph of tasks, calculate the execution order and run it.
		"""
		super().__init__(config, global_config)
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
		"""
		Here, all the tasks in config are instantiated and added as nodes to a nx graph
		"""
		self.task_nodes = {}
		for task_name, task_config in self.config['Tasks'].items():
			task_class = task_config['class']
			task_obj = [getattr(module,task_class) for module in self.task_modules if task_class in utils.get_classes_in_module(module)]
			if len(task_obj) == 0:
				raise Exception('{} not recognized as a task'.format(task_class))
			elif len(task_obj) > 1:
				raise Exception('{} found in multiple task modules. Rename the task in your module to avoid name collisions'.format(task_class))
			task_obj = task_obj[0]
			task_instance = task_obj(task_config,self.global_config)
			task_instance.set_name(task_name)
			self.task_nodes[task_name] = task_instance
			self.graph.add_node(task_instance)

	def connect_tasks(self):
		"""
		Here, edges are created using the dependencies variable from each task
		"""
		for task_name, task in self.task_nodes.items():
			dependencies = task.get_dependencies()
			if len(dependencies)>0:
				for dependency in dependencies:
					self.graph.add_edge(self.task_nodes[dependency],task)

	def load_modules(self):
		"""
		Get all the modules where task definitions are found
		"""
		module_paths = ['core_tasks.py']
		if 'modules' in self.config:
			module_paths_ = self.config['modules']
			if not isinstance(module_paths,list):
				module_paths_ = [module_paths_]
			module_paths.extend(module_paths_)
		self.task_modules = []
		for module_path in module_paths:
			try:
				module = utils.module_from_file(Path(module_path).stem,module_path)
			except:
				try:
					module = utils.module_from_folder(module_path)	
				except:
					raise Exception('Could not import Module {}'.format(module_path))

			self.task_modules.append(module)

	def get_dependency_order(self):
		"""
		Use topological sort to get the order of execution.
		"""
		self.dependency_order = list(nx.topological_sort(self.graph))

	def operation(self):
		"""
		Runs each task in order, gather outputs and inputs.
		"""
		print('Running {}'.format(self.name))
		for task in self.dependency_order:
			print('Running {}'.format(task.name))
			args = [list(itemgetter(*task.config[inp])(self.tasks_io)) for inp in task.inputs]

			out_dict = task.run(*args)
			self.tasks_io.update(out_dict)

		return self.tasks_io


