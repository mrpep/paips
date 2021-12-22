import importlib
import argparse
import datetime

import paips
from paips.utils.settings import symbols
from paips.utils import logger, apply_mods, load_experiment

from kahnfigh import Config
from kahnfigh.utils import IgnorableTag, merge_configs,replace_in_config
try:
    from ruamel.yaml import YAML
except:
    from ruamel_yaml import YAML
from io import StringIO
from pathlib import Path
import copy

from paips.core import TaskGraph

def main():
    argparser = argparse.ArgumentParser(description='Run pipeline from configs')
    argparser.add_argument('config_path', help='Path to YAML config file for running experiment', nargs='+')
    argparser.add_argument('--output_path', type=str, help='Output directory for symbolic links of cache', default='experiments/{}'.format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    argparser.add_argument('--no-caching', dest='no_caching', help='Run all', action='store_true', default=False)
    argparser.add_argument('--mods', dest='mods',type=str, help='Modifications to config file')
    argparser.add_argument('--simulate', dest='simulate', help='Just build graph without executing it', action='store_true', default=False)
    args = vars(argparser.parse_args())

    global_config = {'cache': not args['no_caching'],
                     'in_memory': False,
                     'cache_path': 'cache',
                     'output_path': args['output_path'],
                     'cache_compression': 0}

    paips_logger = logger.get_logger('Paips','logs')
    main_config = load_experiment(args['config_path'], mods=args['mods'],global_config=global_config, logger=paips_logger)
    if 'defaults' in main_config:
        main_config.pop('defaults')

    cluster_manager = None
    if 'cluster_config' in main_config:
        cluster_config = main_config['cluster_config']
        if cluster_config['manager'] == 'ray':
            cluster_manager = 'ray'
            import ray
            try:
                ray.init(address= 'auto', log_to_driver=False) #If existing cluster connects to it
            except:
                ray.init(log_to_driver=False) #Else uses a local cluster

    main_task = TaskGraph(main_config,global_config,name='MainTask',logger=paips_logger,simulate=args['simulate'])
    main_task.run()

    if cluster_manager == 'ray':
        ray.shutdown()

if __name__ == '__main__':
    try:
        main()
    finally:
        ray.shutdown()
