from IPython import embed

import core_tasks
import importlib
import paips
import utils

myconfig = utils.get_config('trust_ml.yaml')
global_config = {'cache': True,
				 'in_memory': False,
				 'cache_dir': 'cache',
				 'output_dir': 'experiments',
				 'list_path': '/home/lpepino/trust-corpus-extras/lists/recorded_at_lab/produced'}

main_task = core_tasks.TaskGraph(myconfig,global_config)
main_task.set_name('Main Task')
main_task.run()

