from IPython import embed
import importlib
import paips
import utils

from core import TaskGraph

myconfig = utils.get_config('musdb18.yaml')
global_config = {'cache': True,
				 'in_memory': False,
				 'cache_dir': 'cache',
				 'output_dir': 'experiments',
				 'cache_compression': 3}

main_task = TaskGraph(myconfig,global_config,name='maintask')
main_task.run()

