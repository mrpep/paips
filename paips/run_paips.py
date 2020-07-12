from IPython import embed
import importlib
import paips
#import paips.utils as utils
#from paips.utils.config_processors import embed_configs

from paips.utils.settings import symbols

from paips.core import TaskGraph
import argparse
from kahnfigh import Config
from paips.utils import logger

def main():
    argparser = argparse.ArgumentParser(description='Run pipeline from configs')
    #argparser.add_argument('config_path', help='Path to YAML config file for running experiment', nargs='+')
    argparser.add_argument('config_path', help='Path to YAML config file for running experiment')
    argparser.add_argument('--no-caching', dest='no_caching', help='Run all', action='store_true', default=False)
    args = vars(argparser.parse_args())

    #Get main config
    main_config = Config(args['config_path'])
    #Get global variables and set to default values the missing ones
    global_config = {'cache': not args['no_caching'],
                     'in_memory': False,
                     'cache_dir': 'cache',
                     'output_dir': 'experiments',
                     'cache_compression': 3}                   
    global_config.update(main_config.get('global',{}))

    paips_logger = logger.get_logger('Paips','logs')

    #Embed external configs and global variables
    main_config.replace_on_symbol(symbols['insert_config'],lambda x: Config(x).store)
    main_config.replace_on_symbol(symbols['insert_variable'],lambda x: global_config[x])

    main_task = TaskGraph(main_config,global_config,name='MainTask',logger=paips_logger)
    main_task.run()

if __name__ == '__main__':
    main()
