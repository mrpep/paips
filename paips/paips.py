import networkx as nx
from IPython import embed
import json
import copy
import hashlib
from pathlib import Path
import joblib
from utils.config_processors import config_get_global_vars

class CacheElement():
	def __init__(self,path):
		self.path = path
	def load(self):
		return joblib.load(self.path)

class Task:
	def __init__(self,config,global_config):
		self.outputs = []

		config = config_get_global_vars(config,global_config)

		self.global_config = global_config
		self.config = config


		self.required_fields = []
		self.input_hashes = {}

		self.cache = config.get('cache',self.global_config['cache'])
		self.in_memory = config.get('in_memory',self.global_config['in_memory'])
		self.cache_dir = Path(self.global_config['cache_dir'])
		self.output_dir = Path(self.global_config['output_dir'])
		if not self.cache_dir.exists():
			self.cache_dir.mkdir(parents=True)
		if not self.output_dir.exists():
			self.output_dir.mkdir(parents=True)

	def get_dependencies(self):
		self.dependencies = []
		for input_data in self.inputs:
			if input_data in self.config:
				input_name = self.config[input_data]
				if not isinstance(input_name,list):
					input_name = [input_name]
				self.dependencies.extend([name.split('.')[0] for name in input_name])
		self.dependencies = list(set(self.dependencies))
		return self.dependencies

	def check_requirements(self):
		for field in self.required_fields:
			if field not in self.config:
				raise Exception('{} field is needed in the config'.format(field))

	def set_name(self,name):
		self.name = name
		
	def save(self,output_dict):
		save_path = Path(self.cache_dir,self.task_hash)
		if not save_path.exists():
			save_path.mkdir(parents=True)

		for out_name, out_val in output_dict.items():
			new_name = out_name.split('.')[-1]

			out_path = Path(save_path,out_name)
			#output_dict[out_name] = '{}/{}'.format(self.task_hash,new_name)
			output_dict[out_name] = CacheElement(out_path)
			joblib.dump(out_val,out_path)
			
		return output_dict 

	def run(self,*args):
		
		self.task_hash = self.make_hash()
		if self.cache and self.find_cache(self.task_hash):
			print('Caching {}'.format(self.name))
			output_dict = {'{}.{}'.format(self.name,out): CacheElement(Path(self.cache_dir,self.task_hash,out)) for out in self.outputs}
			#for out in self.outputs:
			#	output_dict['{}.{}'.format(self.name,out)] = Path(self.cache_dir,self.task_hash,out)
		else:
			args = list(args)
			for i,arg in enumerate(args):
				if isinstance(arg,CacheElement):
					args[i] = arg.load()
				elif isinstance(arg,list):
					args[i] = [arg_i.load() if isinstance(arg_i,CacheElement) else arg_i for arg_i in arg]

			outs = self.operation(*args)
			if outs:
				output_dict = {'{}.{}'.format(self.name,task_name):task_out for task_name,task_out in zip(self.outputs,outs)}
			else:
				output_dict = None

			if not self.in_memory:
				output_dict = self.save(output_dict)

		return output_dict

	def set_input_hashes(self, hashes):
		#Set the hashes of the inputs to track cache history
		self.input_hashes = hashes

	def make_hash(self):
		self.hash_config = copy.deepcopy(self.config)
		#Add dependencies hashes to track execution history:
		for in_name, in_hash in self.input_hashes.items():
			self.hash_config[in_name] = in_hash

		hashable_str = str(json.dumps(self.hash_config,sort_keys=True,default=str,ensure_ascii=True))
		task_hash = hashlib.sha1(hashable_str.encode('utf-8')).hexdigest()
		self.task_hash = task_hash
		return task_hash

	def get_hash(self):
		#Return the hash associated with this task
		return self.task_hash

	def find_cache(self,task_hash):
		#Checks if a file with the corresponding hash exists
		if not Path(self.cache_dir,task_hash).exists():
			return False
		for out in self.outputs:
			if not Path(self.cache_dir,task_hash,out).exists():
				return False
		return True

	