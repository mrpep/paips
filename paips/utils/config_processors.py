from paips.utils import get_config

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

