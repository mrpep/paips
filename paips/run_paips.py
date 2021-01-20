import importlib
import argparse
import datetime

import paips
from paips.core import TaskGraph
from paips.utils.settings import symbols
from paips.utils import logger, apply_mods
from kahnfigh import Config
from kahnfigh.utils import IgnorableTag, merge_configs,replace_in_config
from ruamel.yaml import YAML
from io import StringIO
from pathlib import Path
import copy

from IPython import embed

#def replace_vars(main_config, global_config):
#    main_config.find_path(symbols['insert_variable'],mode='startswith',action=lambda x: global_config[x.split(symbols['insert_variable'])[-1]] if x.split(symbols['insert_variable'])[-1] in global_config else x)

def replace_vars(config, global_config, missing_paths):
    found_paths = config.find_path(symbols['insert_variable'],mode='startswith')
    for path in found_paths:
        tag_data = config[path]
        var_to_insert = tag_data.split(symbols['insert_variable'])[-1]
        if var_to_insert not in global_config:
            missing_paths.append(var_to_insert)
        else:
            config[path] = global_config[var_to_insert]

def insert_yaml_value(config,special_tags,global_config,missing_paths):
    found_paths = config.find_path(symbols['insert_config'],mode='startswith')
    #,action=lambda x: process_config(Config(x.split(symbols['insert_config'])[-1],special_tags=special_tags),special_tags=special_tags,global_config=global_config)
    for path in found_paths:
        tag_data = config[path]
        insert_yaml_path = tag_data.split(symbols['insert_config'])[-1]
        insert_config = Config(insert_yaml_path,special_tags=special_tags)
        global_config.update(insert_config.get('global',{}))
        insert_config = process_config(insert_config,special_tags,global_config,missing_paths)
        config[path] = insert_config

def include_config(config,special_tags,global_config,missing_paths):
    found_paths = config.find_keys('include')
    for p in found_paths:
        includes = config[p]
        for include_config in includes:
            if include_config.get('enable',True) and include_config.get('config',None):               
                path_yaml_to_include = Path(config.yaml_path.parent,include_config.pop('config'))
                imported_config = Config(path_yaml_to_include,special_tags=special_tags)
                mods = include_config.get('mods',None)
                if mods:
                    raise Exception('Mods not implemented in include')
                for r,v in include_config.items():
                    r='({})'.format(r)
                    imported_config = replace_in_config(imported_config,r,v)
                if '/' in p:
                    p_parent = '/'.join(p.split('/')[:-1])
                else:
                    p_parent = None
                imported_config = process_config(imported_config,special_tags,global_config,missing_paths)
                if p_parent:
                    p_config = Config(config[p_parent])
                    p_config.yaml_path = config.yaml_path
                    new_config = merge_configs([p_config,imported_config])
                    config[p_parent] = new_config
                else:
                    original_yaml_path = config.yaml_path
                    config = merge_configs([Config(config),imported_config])
                    config.yaml_path = original_yaml_path
        config.pop(p)
    return config

def add_includes(main_config, special_tags,global_config):
    for k in main_config.find_keys('include'):
        includes = main_config[k]
        imported_configs = []
        for include_config in includes:
            yaml_to_include = Path(main_config.yaml_path.parent,include_config.pop('config'))
            print('Including {} from config {}'.format(yaml_to_include,main_config.yaml_path))
            imported_config = Config(yaml_to_include,special_tags=special_tags)
            for r,v in include_config.items():
                r='({})'.format(r)
                imported_config = replace_in_config(imported_config,r,v)
            if '/' in k:
                k_parent = '/'.join(k.split('/')[:-1])
            else:
                k_parent = None
            imported_config = process_config(imported_config,special_tags,global_config)
            imported_configs.append(imported_config)
        main_config.pop(k)
        if k_parent:
            new_config = merge_configs([Config(main_config[k_parent])]+imported_configs)
            main_config[k_parent] = new_config
        else:
            main_config = merge_configs([Config(main_config)]+imported_configs)
        

    return main_config

def process_config(config,special_tags,global_config,missing_paths):
    replace_vars(config,global_config, missing_paths)
    global_config.update(config.get('global',{}))
    insert_yaml_value(config, special_tags, global_config, missing_paths)
    global_config.update(config.get('global',{}))
    config = include_config(config,special_tags,global_config,missing_paths)

    #replace_vars(config,global_config)
    #global_config.update(config.get('global',{}))
    #config.find_path(symbols['insert_config'],mode='startswith',action=lambda x: process_config(Config(x.split(symbols['insert_config'])[-1],special_tags=special_tags),special_tags=special_tags,global_config=global_config))
    #global_config.update(config.get('global',{}))
    #add_includes(config,special_tags,global_config)
    #global_config.update(config.get('global',{}))

    return config

def replace_yamls(main_config, special_tags):
    main_config.find_path(symbols['insert_config'],mode='startswith',action=lambda x: Config(x.split(symbols['insert_config'])[-1],special_tags=special_tags))
    return main_config

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
    #main_config = merge_configs(configs)
    main_config = configs[0]

    apply_mods(args['mods'], main_config)

    #Get global variables and set to default values the missing ones
    global_config = {'cache': not args['no_caching'],
                     'in_memory': False,
                     'cache_path': 'cache',
                     'output_path': args['output_path'],
                     'cache_compression': 3}

    global_config.update(main_config.get('global',{}))

    if 'global' in main_config:
        main_config['global'].update(global_config)
    else:
        main_config['global'] = global_config

    paips_logger = logger.get_logger('Paips','logs')

    #Embed external configs and global variables

    missing_paths = []
    main_config = process_config(main_config,special_tags,global_config,missing_paths)
    n_tries = 20

    while n_tries>0 and len(missing_paths)>0:
        n_tries-=1
        global_config.update(main_config['global'])
        missing_paths = []
        main_config = process_config(main_config,special_tags,global_config,missing_paths)

    if len(missing_paths)>0:
        raise Exception('Cannot resolve tags: {}'.format(missing_paths))

    #main_config = add_includes(main_config)
    #main_config = replace_vars(main_config)
    #main_config = replace_yamls(main_config, special_tags)
    #global_config = main_config['global']
    #main_config = replace_vars(main_config)
    
    default_cluster_config = {
    'manager': 'ray',
    'n_cores': 1,
    'niceness': 20
    }

    cluster_config = main_config.get('cluster_config',default_cluster_config)
    if cluster_config:
        if cluster_config['manager'] == 'ray':
            import ray
            try:
                ray.init(address= 'auto', log_to_driver=False) #If existing cluster connects to it
            except:
                ray.init(log_to_driver=False) #Else uses a local cluster

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
        parallel_paths_[k] = symbols['nocache'] + ' ' + str(v)
        v_yaml_stream.close()

    for k,v in map_paths_.items():
        v_yaml_stream = StringIO()
        yaml.dump(v,v_yaml_stream)
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
