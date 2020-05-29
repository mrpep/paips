import networkx as nx
from IPython import embed

class Task:
	def __init__(self,config):
		self.config = config
		self.required_fields = []

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
		
	def save(self):
		pass

	def run(self):
		pass

	def get_hash(self):
		#Creates a hash for the current task, using also hashes from dependencies
		pass

	def find_cache(self):
		#Checks if a file with the corresponding hash exists
		pass

	