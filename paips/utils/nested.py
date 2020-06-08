from settings import symbols

def search_dependencies(elem,dependencies):
	if isinstance(elem,dict):
		for k,v in elem.items():
			search_dependencies(v,dependencies)
	elif isinstance(elem,str) and symbols['dot'] in elem:
		dependencies.append(elem.split(symbols['dot'])[0])
	elif isinstance(elem,list):
		for v in elem:
			search_dependencies(v,dependencies)

def search_replace(elem,replacements,action):
	if isinstance(elem,dict):
		for k,v in elem.items():
			if isinstance(v,str) and v in replacements:
				if action == 'load':
					elem[k] = replacements[v].load()
				elif action == 'get_hash':
					elem[k] = replacements[v].get_hash()
			else:
				search_replace(v,replacements,action)
	elif isinstance(elem,list):
		for k,v in enumerate(elem):
			if isinstance(v,str) and v in replacements:
				if action == 'load':
					elem[k] = replacements[v].load()
				elif action == 'get_hash':
					elem[k] = replacements[v].get_hash()
			else:
				search_replace(v,replacements,action)
	else:
		pass