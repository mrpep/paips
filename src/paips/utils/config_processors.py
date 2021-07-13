from ruamel.yaml import YAML
from .settings import symbols
from pathlib import Path
from kahnfigh import Config
from kahnfigh.utils import replace_in_config, merge_configs

def get_config(filename):
    yaml = YAML(typ='safe')
    config = yaml.load(Path(filename))
    return config

def recursive_replace(tree,symbol_to_replace,replace_func):
    if isinstance(tree,dict):
        for k,v in tree.items():
            if isinstance(v,str) and v.startswith(symbol_to_replace):
                tree[k] = replace_func(v.split(symbol_to_replace)[1])
            elif isinstance(v,dict) or isinstance(v,list):
                recursive_replace(v,symbol_to_replace,replace_func)
    elif isinstance(tree,list):
        for k,v in enumerate(tree):
            if isinstance(v,str) and v.startswith(symbol_to_replace):
                tree[k] = replace_func(v.split(symbol_to_replace)[1])
            elif isinstance(v,dict) or isinstance(v,list):
                recursive_replace(v,symbol_to_replace,replace_func)

def config_get_global_vars(config,global_config):
    def global_replace(key):
        return global_config[key]
    recursive_replace(config,symbols['global'],global_replace)
    return config

def config_only_cachables(config):
    pass

def embed_configs(config):
    def config_replace(key):
        return get_config(key)
    recursive_replace(config,symbols['embed'],config_replace)
    return config

def replace_vars(config, global_config, missing_paths):
    found_paths = config.find_path(symbols['insert_variable'],mode='startswith')
    for path in found_paths:
        tag_data = config[path]
        var_to_insert = tag_data.split(symbols['insert_variable'])[-1]
        if var_to_insert not in global_config:
            missing_paths.append(var_to_insert)
        else:
            config[path] = global_config[var_to_insert]

def insert_yaml_value(config,special_tags,global_config,default_config,missing_paths):
    found_paths = config.find_path(symbols['insert_config'],mode='startswith')
    #,action=lambda x: process_config(Config(x.split(symbols['insert_config'])[-1],special_tags=special_tags),special_tags=special_tags,global_config=global_config)
    for path in found_paths:
        tag_data = config[path]
        insert_yaml_path = tag_data.split(symbols['insert_config'])[-1]
        insert_config = Config(insert_yaml_path,yaml_tags=special_tags)
        global_config.update(insert_config.get('global',{}))
        if 'defaults' in insert_config:
            default_config.update(insert_config.pop('defaults'))
        insert_config = process_config(insert_config,special_tags,global_config,default_config,missing_paths)
        config[path] = insert_config

def include_config(config,special_tags,global_config,default_config,missing_paths):
    found_paths = config.find_keys('include')

    for p in found_paths:
        includes = config[p]
        switch = None
        if isinstance(includes,dict):
            switch = includes.get('switch',None)
        if switch is not None:
            if not isinstance(switch,list):
                switch = [switch]
            filtered_includes = []
            for include_config in includes['configs']:
                if include_config.get('name',None) in switch:
                    filtered_includes.append(include_config)
            includes = filtered_includes

        for include_config in includes:
            if include_config.get('enable',True) and include_config.get('config',None):
                path_yaml_to_include = Path(config.yaml_path.parent,include_config.pop('config'))
                
                imported_config = Config(path_yaml_to_include,yaml_tags=special_tags)
                if 'defaults' in imported_config:
                    default_config.update(imported_config.pop('defaults'))
                mods = include_config.get('mods',None)
                for r,v in include_config.items():
                    r='({})'.format(r)
                    imported_config = replace_in_config(imported_config,r,v)
                if '/' in p:
                    p_parent = '/'.join(p.split('/')[:-1])
                else:
                    p_parent = None
                imported_config = process_config(imported_config,special_tags,global_config,default_config,missing_paths)
                if mods:
                    apply_mods(mods,imported_config)
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

def add_missing(dict_to_update, defaults):
    keys_to_delete = []
    for k,v in defaults.items():
        if k not in dict_to_update:
            dict_to_update[k] = v
            keys_to_delete.append(k)
    for k in keys_to_delete:
        defaults.pop(k)

def process_config(config,special_tags,global_config,default_config,missing_paths):
    add_missing(global_config,default_config)
    global_config.update(config.get('global',{}))
    
    replace_vars(config,global_config, missing_paths)
    global_config.update(config.get('global',{}))
    add_missing(global_config,default_config)
    insert_yaml_value(config, special_tags, global_config, default_config, missing_paths)
    global_config.update(config.get('global',{}))
    add_missing(global_config,default_config)

    config = include_config(config,special_tags,global_config,default_config,missing_paths)

    return config

def replace_yamls(main_config, special_tags):
    main_config.find_path(symbols['insert_config'],mode='startswith',action=lambda x: Config(x.split(symbols['insert_config'])[-1],special_tags=special_tags))
    return main_config

def task_parameters_level_from_path(path):
    l = path.split('/')
    idx_parent_tasks = len(l) - 1 - l[::-1].index('Tasks')
    parent_path = '/'.join(l[:idx_parent_tasks+2])
    return parent_path

def apply_mods(modstr,config):
    yaml = YAML()
    if modstr is not None:
        if isinstance(modstr,str):
            mods = modstr.split('&')
            for mod in mods:
                if '=' in mod:
                    mod_parts = mod.split('=')
                    mod_k = '='.join(mod_parts[:-1])
                    mod_v = mod_parts[-1]
                    #if mod_parts[1].startswith('['):
                    if '!' in mod_v:
                        config[mod_k] = mod_v
                    #elif mod_parts[1].lower() == 'null':
                    #    config[mod_parts[0]] = None
                    else:
                        config[mod_k] = yaml.load(mod_v)
                        
        elif isinstance(modstr,list):
            for mod in modstr:
                config.update(Config(mod).to_shallow())

def get_delete_param(dictionary,param,default_value=None):
    if param in dictionary:
        return dictionary.pop(param)
    else:
        return default_value