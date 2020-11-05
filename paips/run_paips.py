import importlib
import argparse
import datetime

import paips
from paips.core import TaskGraph
from paips.utils.settings import symbols
from paips.utils import logger, apply_mods
from kahnfigh import Config
from kahnfigh.utils import IgnorableTag, merge_configs
from ruamel.yaml import YAML
from io import StringIO

def main():
    argparser = argparse.ArgumentParser(description='Run pipeline from configs')
    argparser.add_argument('config_path', help='Path to YAML config file for running experiment', nargs='+')
    argparser.add_argument('--output_path', type=str, help='Output directory for symbolic links of cache', default='experiments/{}'.format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    argparser.add_argument('--no-caching', dest='no_caching', help='Run all', action='store_true', default=False)
    argparser.add_argument('--mods', dest='mods',type=str, help='Modifications to config file')
    args = vars(argparser.parse_args())

    #Get main config
    #By default, yaml uses custom tags marked as !, however, we want to use it in a more general way even in dictionaries.
    #To avoid raising exceptions, an ignorable tag is created which will return the string unchanged for later processing

    ignorable_tags = [v.strip() for k,v in symbols.items() if v.startswith('!')]
    special_tags = [IgnorableTag(tag) for tag in ignorable_tags]

    configs = [Config(path_i, special_tags = special_tags) for path_i in args['config_path']]
    main_config = merge_configs(configs)

    apply_mods(args['mods'], main_config)

    #Get global variables and set to default values the missing ones
    global_config = {'cache': not args['no_caching'],
                     'in_memory': False,
                     'cache_path': 'cache',
                     'output_path': args['output_path'],
                     'cache_compression': 3}

    global_config.update(main_config.get('global',{}))
    main_config['global'].update(global_config)

    paips_logger = logger.get_logger('Paips','logs')

    #Embed external configs and global variables

    main_config.find_path(symbols['insert_config'],mode='startswith',action=lambda x: Config(x.split(symbols['insert_config'])[-1],special_tags=special_tags))
    global_config = main_config['global']
    main_config.find_path(symbols['insert_variable'],mode='startswith',action=lambda x: global_config[x.split(symbols['insert_variable'])[-1]])

    default_cluster_config = {
    'manager': 'ray',
    'n_cores': 1,
    'niceness': 20
    }

    cluster_config = main_config.get('cluster_config',default_cluster_config)
    if cluster_config:
        if cluster_config['manager'] == 'ray':
            import ray
            ray.init(log_to_driver=False)
            #ray.init()

    def task_parameters_level_from_path(path):
        l = path.split('/')
        idx_parent_tasks = len(l) - 1 - l[::-1].index('Tasks')
        parent_path = '/'.join(l[:idx_parent_tasks+2])
        return parent_path

    #For every task with a variable that we want to loop, 
    #we find the tag and create a parameter 'parallel' which holds the names
    #of the loopable params, and adds a '!nocache' so that it is not cached

    parallel_paths = main_config.find_path(symbols['distributed-pool'],mode='startswith',action='remove_substring') 
    parallel_paths = [(task_parameters_level_from_path(p),p.split(task_parameters_level_from_path(p) + '/')[-1]) for p in parallel_paths]
    
    parallel_paths_async = [k for k in list(main_config.all_paths()) if k.endswith('async') and main_config[k] == True]
    parallel_paths_async = [(task_parameters_level_from_path(p),p.split(task_parameters_level_from_path(p) + '/')[-1]) for p in parallel_paths_async]

    parallel_paths_ = {}

    for p in parallel_paths_async:
        main_config[p[0]+'/niceness'] = cluster_config['niceness']
    for p in parallel_paths:
        path = p[0]+'/parallel'
        if path not in parallel_paths_:
            parallel_paths_[path] = [p[1]]
        else:
            parallel_paths_[path].append(p[1])
        if 'n_cores' not in main_config[p[0]]:
            main_config[p[0]+'/n_cores'] = cluster_config['n_cores']
        if 'niceness' not in main_config[p[0]]:
            main_config[p[0]+'/niceness'] = cluster_config['niceness']

    map_paths = main_config.find_path(symbols['serial-map'],mode='startswith',action='remove_substring')
    map_paths = [(task_parameters_level_from_path(p),p.split(task_parameters_level_from_path(p) + '/')[-1]) for p in map_paths]
    map_paths_ = {}

    for p in map_paths:
        path = p[0] + '/map_vars'
        if path not in map_paths_:
            map_paths_[path] = [p[1]]
        else:
            map_paths_[path].append(p[1])

    yaml = YAML()
    for k,v in parallel_paths_.items():
        v_yaml_stream = StringIO()
        yaml.dump(v,v_yaml_stream)
        #parallel_paths_[k] = symbols['nocache'] + ' ' + v_yaml_stream.getvalue()
        parallel_paths_[k] = symbols['nocache'] + ' ' + str(v)
        v_yaml_stream.close()

    for k,v in map_paths_.items():
        v_yaml_stream = StringIO()
        yaml.dump(v,v_yaml_stream)
        #map_paths_[k] = symbols['nocache'] + ' ' + v_yaml_stream.getvalue()
        map_paths_[k] = symbols['nocache'] + ' ' + str(v)
        v_yaml_stream.close()

    main_config.update(parallel_paths_)
    main_config.update(map_paths_)

    main_task = TaskGraph(main_config,global_config,name='MainTask',logger=paips_logger)

    main_task.run()
    ray.shutdown()

if __name__ == '__main__':
    try:
        main()
    finally:
        ray.shutdown()
