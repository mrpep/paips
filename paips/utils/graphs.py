import networkx as nx
from kahnfigh import Config
from IPython import embed
from .settings import symbols
from kahnfigh.utils import IgnorableTag, merge_configs, replace_in_config
from .config_processors import apply_mods, task_parameters_level_from_path, process_config
from ruamel.yaml import YAML

def make_graph_from_tasks(task_nodes):
    graph = nx.DiGraph()
    for task_name, task in task_nodes.items():
        dependencies = task.search_dependencies()
        if len(dependencies)>0:
            for dependency in dependencies:
                graph.add_edge(task_nodes[dependency],task)
                
    return graph

def load_experiment(configs, mods=None, global_config=None, logger=None):
    #Get main config
    #By default, yaml uses custom tags marked as !, however, we want to use it in a more general way even in dictionaries.
    #To avoid raising exceptions, an ignorable tag is created which will return the string unchanged for later processing

    ignorable_tags = [v.strip() for k,v in symbols.items() if v.startswith('!')]
    special_tags = [IgnorableTag(tag) for tag in ignorable_tags]

    configs = [Config(path_i, special_tags = special_tags) for path_i in configs]
    #main_config = merge_configs(configs)
    main_config = configs[0]
    apply_mods(mods, main_config)

    if global_config is None:
        global_config = {}
    global_config.update(main_config.get('global',{}))
    default_config = main_config.get('defaults', {})

    if 'global' in main_config:
        main_config['global'].update(global_config)
    else:
        main_config['global'] = global_config

    #Config processing/merging/expanding
    missing_paths = []
    main_config = process_config(main_config,special_tags,global_config,default_config,missing_paths)
    n_tries = 20

    while n_tries>0 and len(missing_paths)>0:
        n_tries-=1
        global_config.update(main_config['global'])
        default_config.update(main_config.get('default',{}))
        missing_paths = []
        main_config = process_config(main_config,special_tags,global_config,default_config, missing_paths)

    if len(missing_paths)>0:
        print('Warning: Cannot resolve tags {}'.format(missing_paths))
        for k in missing_paths:
            global_config[k] = None
        missing_paths = []
        main_config = process_config(main_config,special_tags,global_config,missing_paths)

    default_cluster_config = {
        'manager': 'ray',
        'n_cores': 1,
        'niceness': 20
        }

    cluster_config = main_config.get('cluster_config',default_cluster_config)
    main_config['cluster_config'] = cluster_config
    main_config['global_config'] = global_config

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

    #main_task = TaskGraph(main_config,global_config,name='MainTask',logger=paips_logger)

    return main_config