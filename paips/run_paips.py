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
				 'list_path': '/home/lpepino/trust-corpus-extras/lists/recorded_at_lab/produced'}

main_task = TaskGraph(myconfig,global_config,name='maintask')
main_task.run()

