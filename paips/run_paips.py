from IPython import embed
import importlib
import paips
import paips.utils as utils

from paips.core import TaskGraph
import argparse

def main():
    argparser = argparse.ArgumentParser(description='Run pipeline from configs')
    #argparser.add_argument('config_path', help='Path to YAML config file for running experiment', nargs='+')
    argparser.add_argument('config_path', help='Path to YAML config file for running experiment')
    argparser.add_argument('--no-caching', dest='no_caching', help='Run all', action='store_true', default=False)
    args = vars(argparser.parse_args())

    myconfig = utils.get_config(args['config_path'])
    global_config = {'cache': not args['no_caching'],
                     'in_memory': False,
                     'cache_dir': 'cache',
                     'output_dir': 'experiments',
                     'cache_compression': 3}

    main_task = TaskGraph(myconfig,global_config,name='MainTask')
    main_task.run()

if __name__ == '__main__':
    main()
