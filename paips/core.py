from utils import get_delete_param, make_hash, search_dependencies, search_replace, find_cache, get_modules, get_classes_in_module
from IPython import embed
import copy
import joblib
from pathlib import Path
import networkx as nx

class TaskIO():
	def __init__(self, data, hash_val, iotype = 'data', name = None):
		self.hash = hash_val
		self.data = data
		self.iotype = iotype
		self.name = name

	def get_hash(self):
		return self.hash

	def load(self):
		if self.iotype == 'data':
			return self.data
		elif self.iotype == 'path':
			return joblib.load(self.data)

	def save(self, path):
		destination_path = Path(path,self.hash)
		if not destination_path.exists():
			destination_path.mkdir(parents=True)

		joblib.dump(self.data,Path(destination_path,self.name))
		return TaskIO(Path(destination_path,self.name),self.hash,iotype='path',name=self.name)

class Task():
	def __init__(self, parameters, global_parameters=None, name=None, logger=None):

		self.global_parameters = {'cache': True,
							 'cache_path': 'cache'}

		if global_parameters:
			self.global_parameters.update(global_parameters)

		self.name = name
		self.valid_args=[]
		self.output_names =	get_delete_param(parameters,'output_names',['out'])
		self.cache = get_delete_param(parameters,'cache',self.global_parameters['cache'])
		self.in_memory = get_delete_param(parameters,'in_memory',self.global_parameters['in_memory'])
		self.parameters = parameters
		self.dependencies = []
		self.logger = logger
		self.hash_dict = copy.deepcopy(self.parameters)


	def search_dependencies(self):
		search_dependencies(self.parameters,self.dependencies)
		self.dependencies = list(set(self.dependencies))
		return self.dependencies

	def check_valid_args(self):
		for k in self.parameters.keys():
			if k not in self.valid_args:
				raise Exception('{} not recognized as a valid parameter'.format(k))

	def send_dependency_data(self,data):
		"""
		Replace TaskIOs in parameters with the corresponding data. Also adds its associated hashes to the hash dictionary
		"""
		search_replace(self.hash_dict,data,action='get_hash')
		search_replace(self.parameters,data,action='load')

	def get_hash(self):
		return make_hash(self.hash_dict)

	def process(self):
		pass

	def run(self):
		task_hash = self.get_hash()
		cache_paths = find_cache(task_hash,self.global_parameters['cache_path'])
		if self.cache and cache_paths:
			print('Caching task {}'.format(self.name))
			out_dict = {'{}.{}'.format(self.name,Path(cache_i).stem): TaskIO(cache_i,task_hash,iotype='path',name=Path(cache_i).stem) for cache_i in cache_paths}
		else:
			print('Running task {}'.format(self.name))
			outs = self.process()
			if not isinstance(outs,tuple):
				outs = (outs,)

			out_dict = {'{}.{}'.format(self.name,out_name): TaskIO(out_val,task_hash,iotype='data',name=out_name) for out_name, out_val in zip(self.output_names,outs)}
		
			if not self.in_memory:
				print('Saving outputs from task {}'.format(self.name))
				for k,v in out_dict.items():
					if v.iotype == 'data':
						out_dict[k] = v.save(self.global_parameters['cache_path'])	

		return out_dict 

class TaskGraph(Task):
	def __init__(self,parameters,global_parameters=None, name=None, logger=None):
		super().__init__(parameters,global_parameters,name,logger)
		#Gather modules:
		self.external_modules = self.parameters.get('modules',[])
		self.external_modules = self.external_modules + self.global_parameters.get('modules',[])
		self.load_modules()
		#Build the graph
		self.graph = nx.DiGraph()
		self.gather_tasks()
		self.connect_tasks()
		#Get tasks execution order
		self.get_dependency_order()

	def load_modules(self):
		self.task_modules = get_modules(self.external_modules)

	def gather_tasks(self):
		"""
		Here, all the tasks in config are instantiated and added as nodes to a nx graph
		"""
		self.task_nodes = {}
		for task_name, task_config in self.parameters['Tasks'].items():
			task_class = task_config['class']
			task_obj = [getattr(module,task_class) for module in self.task_modules if task_class in get_classes_in_module(module)]
			if len(task_obj) == 0:
				raise Exception('{} not recognized as a task'.format(task_class))
			elif len(task_obj) > 1:
				raise Exception('{} found in multiple task modules. Rename the task in your module to avoid name collisions'.format(task_class))
			task_obj = task_obj[0]
			task_instance = task_obj(task_config,self.global_parameters,task_name,self.logger)
			self.task_nodes[task_name] = task_instance
			self.graph.add_node(task_instance)

	def connect_tasks(self):
		"""
		Here, edges are created using the dependencies variable from each task
		"""
		for task_name, task in self.task_nodes.items():
			dependencies = task.search_dependencies()
			if len(dependencies)>0:
				for dependency in dependencies:
					self.graph.add_edge(self.task_nodes[dependency],task)

	def get_dependency_order(self):
		"""
		Use topological sort to get the order of execution.
		"""
		self.dependency_order = list(nx.topological_sort(self.graph))

	def process(self):
		"""
		Runs each task in order, gather outputs and inputs.
		"""
		self.tasks_io = {}
		for task in self.dependency_order:
			task.send_dependency_data(self.tasks_io)
			out_dict = task.run()
			self.tasks_io.update(out_dict)

		return self.tasks_io
	




	