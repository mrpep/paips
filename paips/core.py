from .utils import get_delete_param, make_hash, search_dependencies, search_replace, find_cache, get_modules, get_classes_in_module, make_graph_from_tasks, symbols
from IPython import embed
import copy
import joblib
from pathlib import Path
import networkx as nx
from kahnfigh import Config
from kahnfigh.core import find_path
from ruamel.yaml import YAML
import os

class TaskIO():
	def __init__(self, data, hash_val, iotype = 'data', name = None, parent = None):
		self.hash = hash_val
		self.data = data
		self.iotype = iotype
		self.name = name
		self.parent = parent
		self.link_path = None

	def get_hash(self):
		return self.hash

	def load(self):
		if self.iotype == 'data':
			return self.data
		elif self.iotype == 'path':
			return joblib.load(self.data)

	def save(self, cache_path=None, export_path=None, compression_level = 0):
		self.address = Path(cache_path,self.hash)
		if not self.address.exists():
			self.address.mkdir(parents=True)
			
		#Save cache:
		joblib.dump(self.data,Path(self.address,self.name),compress=compression_level)

		self.create_link(self.address,export_path)

		return TaskIO(Path(self.address,self.name),self.hash,iotype='path',name=self.name)

	def create_link(self, cache_path, export_path):
		#Create symbolic link to cache:
		self.link_path = Path(export_path,self.parent)
		if not self.link_path.exists():
			os.symlink(str(cache_path.absolute()),str(self.link_path.absolute()))


class Task():
	def __init__(self, parameters, global_parameters=None, name=None, logger=None):

		self.global_parameters = {'cache': True,
							 'cache_path': 'cache',
							 'cache_compression': 0,
							 'output_path': 'experiments'}

		if global_parameters:
			self.global_parameters.update(global_parameters)

		self.name = name
		self.valid_args=[]

		self.parameters = parameters

		#self.output_names =	get_delete_param(self.parameters,'output_names',['out'])
		self.output_names = self.parameters.pop('output_names',['out'])
		self.cache = get_delete_param(self.parameters,'cache',self.global_parameters['cache'])
		self.in_memory = get_delete_param(self.parameters,'in_memory',self.global_parameters['in_memory'])

		self.dependencies = []
		self.logger = logger

		self.hash_dict = copy.deepcopy(self.parameters)

		#Remove not cacheable parameters
		if not isinstance(self.hash_dict, Config):
			self.hash_dict = Config(self.hash_dict)
		if not isinstance(self.parameters, Config):
			self.parameters = Config(self.parameters)

		_ = self.hash_dict.find_path(symbols['nocache'],mode='startswith',action='remove_value')
		_ = self.parameters.find_path(symbols['nocache'],mode='startswith',action='remove_substring')

	def search_dependencies(self):
		dependency_paths = self.parameters.find_path(symbols['dot'],mode='contains')
		#search_dependencies(self.parameters,self.dependencies)
		self.dependencies = [self.parameters[path].split(symbols['dot'])[0] for path in dependency_paths]
		return self.dependencies

	def check_valid_args(self):
		for k in self.parameters.keys():
			if k not in self.valid_args:
				raise Exception('{} not recognized as a valid parameter'.format(k))

	def send_dependency_data(self,data):
		"""
		Replace TaskIOs in parameters with the corresponding data. Also adds its associated hashes to the hash dictionary
		"""
		for k,v in data.items():
			paths = self.hash_dict.find_path(k,action='replace',replace_value=v.get_hash())
			if len(paths) > 0:
				self.parameters.find_path(k,action='replace',replace_value=v.load())

		#search_replace(self.hash_dict,data,action='get_hash')
		#search_replace(self.parameters,data,action='load')

	def get_hash(self):
		return make_hash(self.hash_dict)

	def process(self):
		pass

	def find_cache(self):
		cache_paths = find_cache(self.task_hash,self.global_parameters['cache_path'])
		return cache_paths

	def run(self):
		self.task_hash = self.get_hash()
		self.cache_dir = Path(self.global_parameters['cache_path'],self.task_hash)
		
		cache_paths = self.find_cache()
		if self.cache and cache_paths:
			self.logger.info('Caching task {}'.format(self.name))
			out_dict = {'{}{}{}'.format(self.name,symbols['dot'],Path(cache_i).stem): TaskIO(cache_i,self.task_hash,iotype='path',name=Path(cache_i).stem,parent=self.name) for cache_i in cache_paths}
			for task_name, task in out_dict.items():
				task.create_link(Path(task.data).parent,self.global_parameters['output_path'])
		else:
			self.logger.info('Running task {}'.format(self.name))
			outs = self.process()
			if not isinstance(outs,tuple):
				outs = (outs,)

			out_dict = {'{}{}{}'.format(self.name,symbols['dot'],out_name): TaskIO(out_val,self.task_hash,iotype='data',name=out_name,parent=self.name) for out_name, out_val in zip(self.output_names,outs)}

			if not self.in_memory:
				self.logger.info('Saving outputs from task {}'.format(self.name))
				for k,v in out_dict.items():
					if v.iotype == 'data':
						out_dict[k] = v.save(
							cache_path=self.global_parameters['cache_path'],
							export_path=self.global_parameters['output_path'],
							compression_level=self.global_parameters['cache_compression'])	

		return out_dict 

class TaskGraph(Task):
	def __init__(self,parameters,global_parameters=None, name=None, logger=None):
		super().__init__(parameters,global_parameters,name,logger)
		#Gather modules:
		self.external_modules = self.parameters.get('modules',[])
		self.external_modules = self.external_modules + self.global_parameters.get('modules',[])
		self.target = self.parameters.get('target',None)

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
			task_instance = task_obj(copy.deepcopy(task_config),self.global_parameters,task_name,self.logger)
			self.task_nodes[task_name] = task_instance
			#self.graph.add_node(task_instance)

	def connect_tasks(self):
		"""
		Here, edges are created using the dependencies variable from each task
		"""
		self.graph = make_graph_from_tasks(self.task_nodes)

	def get_dependency_order(self):
		"""
		Use topological sort to get the order of execution. If a target task is specified, find the shortest path.
		"""
		self.dependency_order = list(nx.topological_sort(self.graph))

		if self.target:
			#Si tengo que ejecutar el DAG hasta cierto nodo, primero me fijo que nodo es:
			target_node = [node for node in self.dependency_order if node.name == self.target][0]
			target_idx = self.dependency_order.index(target_node)
			#Despues trunco la lista hasta el nodo, con esto estaria sacando todas las tareas que se iban a ejecutar despues:
			self.dependency_order = self.dependency_order[:target_idx+1]
			#Con esto puedo armar otro grafo que solo contenga los nodos que se iban a ejecutar antes que target.
			reduced_task_nodes = {node.name: node for node in self.dependency_order}
			pruned_graph = make_graph_from_tasks(reduced_task_nodes)
			#Es posible que algunas tareas se ejecutaran antes que target pero que no fueran necesarias para target sino que para un nodo posterior.
			#Estas tareas quedarian desconectadas del target. Busco los subgrafos conectados:
			connected_subgraphs = list(nx.components.connected_component_subgraphs(pruned_graph.to_undirected()))
			#Si hay mas de uno es porque quedaron tareas que no llevan a ningun lado. Agarro el subgrafo con la tarea target:
			if len(connected_subgraphs)>1:
				reachable_subgraph = [g for g in connected_subgraphs if target_node in g.nodes][0]
			else:
				reachable_subgraph = connected_subgraphs[0]
			#Armo el grafo de nuevo porque el algoritmo de subgrafos conectados necesita que sea un UAG.
			reduced_task_nodes = {node.name: node for node in reachable_subgraph.nodes}
			pruned_graph = make_graph_from_tasks(reduced_task_nodes)
			#Topological sort del grafo resultante me da las dependencias para el target task:
			self.dependency_order = list(nx.topological_sort(pruned_graph))
			
	def _clear_tasksio_not_needed(self, remaining_tasks):
		needed_tasks = [list(self.graph.predecessors(node)) for node in self.graph.nodes if node.name in remaining_tasks]
		needed_tasks = [task.name for predecessors in needed_tasks for task in predecessors]

		tasks_io = copy.deepcopy(self.tasks_io)
		for io_name,io_value in tasks_io.items():
			task_producer = io_name.split(symbols['dot'])[0]
			if task_producer not in needed_tasks:
				self.tasks_io.pop(io_name)

	def process(self):
		"""
		Runs each task in order, gather outputs and inputs.
		"""

		"""
		ToDo:
		- Loop execution mode
		"""

		remaining_tasks = [task.name for task in self.dependency_order]
		self.tasks_io = {}
		for task in self.dependency_order:
			task.send_dependency_data(self.tasks_io)
			out_dict = task.run()
			self.tasks_io.update(out_dict)
			remaining_tasks.remove(task.name)
			self._clear_tasksio_not_needed(remaining_tasks)

		return [self.tasks_io]
	




	