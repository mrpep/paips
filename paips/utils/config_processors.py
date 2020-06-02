from IPython import embed

symbols = {'global': '$',
		   'no-cachable': '!'}

def recursive_global_replace(tree,global_config):
	if isinstance(tree,dict):
		for k,v in tree.items():
			if isinstance(v,str) and v.startswith(symbols['global']):
				tree[k] = global_config[v.split(symbols['global'])[1]]
			elif isinstance(v,dict) or isinstance(v,list):
				recursive_global_replace(v,global_config)
	elif isinstance(tree,list):
		for k,v in enumerate(tree):
			if isinstance(v,str) and v.startswith(symbols['global']):
				tree[k] = global_config[v.split(symbols['global'])[1]]
			elif isinstance(v,dict) or isinstance(v,list):
				recursive_global_replace(v,global_config)

def config_get_global_vars(config,global_config):
    recursive_global_replace(config,global_config)
    return config

def config_only_cachables(config):
	pass
