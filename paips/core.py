from .utils import get_delete_param, make_hash, search_dependencies, search_replace, find_cache, get_modules, get_classes_in_module, make_graph_from_tasks, symbols, method_wrapper
from IPython import embed
import copy
import numpy as np
import joblib
from pathlib import Path
import networkx as nx
from kahnfigh import Config
from kahnfigh.core import find_path
from ruamel.yaml import YAML
import os
import ray
from shutil import copyfile

class TaskIO():
    def __init__(self, data, hash_val, iotype = 'data', name = None,position='0'):
        self.hash = hash_val
        self.data = data
        self.iotype = iotype
        self.name = name
        self.link_path = None
        if position:
            self.hash = self.hash + position

    def get_hash(self):
        return self.hash

    def load(self):
        if self.iotype == 'data':
            return self.data
        elif self.iotype == 'path':
            return joblib.load(self.data)

    def save(self, cache_path=None, export_path=None, compression_level = 0, export=False):
        self.address = Path(cache_path,self.hash)
        if not self.address.exists():
            self.address.mkdir(parents=True)
            
        #Save cache:
        try:
            joblib.dump(self.data,Path(self.address,self.name),compress=compression_level)
        except:
            embed()

        if export:
            destination_path = Path(export_path,self.name)
            if not destination_path.parent.exists():
                destination_path.parent.mkdir(parents=True,exist_ok=True)
            copyfile(str(Path(self.address,self.name).absolute()),str(destination_path.absolute()))
        else:
            self.create_link(self.address,export_path)

        return TaskIO(Path(self.address,self.name),self.hash,iotype='path',name=self.name,position=None)

    def create_link(self, cache_path, export_path):
        #Create symbolic link to cache:
        self.link_path = Path(export_path)
        if not self.link_path.parent.exists():
            self.link_path.parent.mkdir(parents=True,exist_ok=True)
        if not self.link_path.exists():
            os.symlink(str(cache_path.absolute()),str(self.link_path.absolute()))

    def __getstate__(self):
        return self.__dict__
    

    def __setstate__(self,d):
        self.__dict__ = d

class Task():
    def __init__(self, parameters, global_parameters=None, name=None, logger=None):

        self.global_parameters = {'cache': True,
                             'cache_path': 'cache',
                             'cache_compression': 0,
                             'output_path': 'experiments'}

        if global_parameters:
            self.global_parameters.update(global_parameters)

        if not Path(self.global_parameters['output_path']).exists():
            Path(self.global_parameters['output_path']).mkdir(parents=True)

        self.name = name
        self.valid_args=[]

        self.parameters = parameters

        #self.output_names =    get_delete_param(self.parameters,'output_names',['out'])
        self.output_names = self.parameters.pop('output_names',['out'])
        self.cache = get_delete_param(self.parameters,'cache',self.global_parameters['cache'])
        self.in_memory = get_delete_param(self.parameters,'in_memory',self.global_parameters['in_memory'])

        self.dependencies = []
        self.logger = logger

        self.make_hash_dict()
        self.initial_parameters = copy.deepcopy(self.parameters)

        self.export_path = Path(self.global_parameters.get('output_path'),self.name)
        self.export = self.parameters.get('export',False)

        fname = Path(self.global_parameters['output_path'],'configs','{}.yaml'.format(self.name))
        self.parameters.save(fname)

    def make_hash_dict(self):
        self.hash_dict = copy.deepcopy(self.parameters)
        #Remove not cacheable parameters
        if not isinstance(self.hash_dict, Config):
            self.hash_dict = Config(self.hash_dict)
        if not isinstance(self.parameters, Config):
            self.parameters = Config(self.parameters)

        _ = self.hash_dict.find_path(symbols['nocache'],mode='startswith',action='remove_value')
        _ = self.parameters.find_path(symbols['nocache'],mode='startswith',action='remove_substring')

        for k,v in self.hash_dict.to_shallow().items():
            if isinstance(v,TaskIO):
                self.hash_dict[k] = self.hash_dict[k].get_hash()


    def search_dependencies(self):
        stop_propagate_dot = self.parameters.get('stop_propagate_dot',None)
        dependency_paths = self.parameters.find_path(symbols['dot'],mode='contains')
        #dependency_paths = [p for p in dependency_paths if 'Tasks' not in ]
        if self.__class__.__name__ == 'TaskGraph':
            dependency_paths = [p for p in dependency_paths if ('Tasks' not in p) and (not p.startswith('outputs'))]
        #Esto es porque dienen tambien usa el simbolo -> entonces debo decir que si encuentra ahi no lo tenga en cuenta.
        if stop_propagate_dot:
            dependency_paths = [p for p in dependency_paths if not p.startswith(stop_propagate_dot)]
        #search_dependencies(self.parameters,self.dependencies)
        self.dependencies = [self.parameters[path].split(symbols['dot'])[0] for path in dependency_paths]
        self.dependencies = [d for d in self.dependencies if d != 'self']

        return self.dependencies

    def reset_task_state(self):
        self.parameters = copy.deepcopy(self.initial_parameters)
        self.make_hash_dict()

    def check_valid_args(self):
        for k in self.parameters.keys():
            if k not in self.valid_args:
                raise Exception('{} not recognized as a valid parameter'.format(k))

    def send_dependency_data(self,data):
        """
        Replace TaskIOs in parameters with the corresponding data. Also adds its associated hashes to the hash dictionary
        """
        for k,v in data.items():
            paths = self.hash_dict.find_path(k,action=lambda x: v.get_hash())
            if len(paths) > 0:
                self.parameters.find_path(k,action=lambda x: v.load())

        #search_replace(self.hash_dict,data,action='get_hash')
        #search_replace(self.parameters,data,action='load')

    def get_hash(self):
        return make_hash(self.hash_dict)

    def process(self):
        pass

    def find_cache(self):
        cache_paths = find_cache(self.task_hash,self.global_parameters['cache_path'])
        return cache_paths

    def _process_outputs(self,outs):
        if isinstance(outs,ray._raylet.ObjectRef):
            filter_outputs = self.parameters.get('outputs',None)
            if filter_outputs:
                self.output_names = []
                for k,v in filter_outputs.items():
                    self.output_names.append(k)

        if not isinstance(outs,tuple):
            outs = (outs,)

        out_dict = {'{}{}{}'.format(self.name,symbols['dot'],out_name): TaskIO(out_val,self.get_hash(),iotype='data',name=out_name,position=str(i)) for i, (out_name, out_val) in enumerate(zip(self.output_names,outs))}
        
        if not self.in_memory:
            self.logger.info('{}: Saving outputs'.format(self.name))
            for k,v in out_dict.items():
                if v.iotype == 'data':
                    out_dict[k] = v.save(
                        cache_path=self.global_parameters['cache_path'],
                        export_path=self.export_path,
                        compression_level=self.global_parameters['cache_compression'],
                        export=self.export)
        return out_dict

    def _parallel_run_ray(self,run_async = False):
        from ray.util.multiprocessing.pool import Pool

        def set_niceness(niceness): # pool initializer
            os.nice(niceness)

        def worker_wrapper(x):
            os.nice(self.parameters['niceness'])
            for k, v in zip(self.parameters['parallel'],x):
                self.parameters[k] = v
            out = self.process()
            return out

        iterable_vars = list(zip(*[self.parameters[k] for k in self.parameters['parallel']]))
        pool = Pool(processes=self.parameters['n_cores'], initializer=set_niceness,initargs=(self.parameters['niceness'],))
        outs = pool.map(worker_wrapper,iterable_vars)

        return self._process_outputs(outs)

    def _serial_run(self,run_async=False):
        if run_async:
            import ray
            import os
            def run_process_async(self):
                os.nice(self.parameters['niceness'])
                self.logger.info('{}: Setting niceness {}'.format(self.name, self.parameters['niceness']))
                return self.process()
            outs = ray.remote(run_process_async).remote(self)
        else:
            outs = self.process()
        return self._process_outputs(outs)

    def _serial_map(self,iteration=None,run_async=False):
        self.initial_parameters = copy.deepcopy(self.parameters)
        self.original_name = copy.deepcopy(self.name)
        self.original_export_path = copy.deepcopy(self.export_path)

        map_var_names = self.parameters['map_vars']
        map_vars = zip(*[self.parameters[k].load() for k in map_var_names])

        if iteration is not None:
            map_vars = list(map_vars)
            map_vars = [map_vars[iteration]]
            initial_iter = iteration
        else:
            initial_iter = 0

        outs = []
        
        for i, iteration in enumerate(map_vars):
            self.parameters = copy.deepcopy(self.initial_parameters)
            self.parameters['iter'] = i + initial_iter
            #self.name = self.original_name + '_{}'.format(i + initial_iter)
            self.cache_dir = Path(self.global_parameters['cache_path'],self.task_hash)
            self.export_path = Path(self.original_export_path,str(i))

            self.make_hash_dict()
            self.task_hash = self.get_hash()

            for k, var in zip(map_var_names,iteration):
                self.parameters[k] = TaskIO(var,self.task_hash,iotype='data',name=k)

            cache_paths = self.find_cache()
            if self.cache and cache_paths:
                self.logger.info('Caching task {}'.format(self.name))
                out_dict = {'{}{}{}'.format(self.name,symbols['dot'],Path(cache_i).stem): TaskIO(cache_i,self.task_hash,iotype='path',name=Path(cache_i).stem,position=str(self.output_names.index(Path(cache_i).stem))) for cache_i in cache_paths}
                #what is this
                for task_name, task in out_dict.items():
                    task.create_link(Path(task.data).parent,self.global_parameters['output_path'])
            else:
                outs.append(self._serial_run(run_async=run_async))
            print('serial map')

        #Restore original parameters
        self.parameters = copy.deepcopy(self.initial_parameters)
        self.name = copy.deepcopy(self.original_name)
        self.export_path = Path(self.original_export_path,'merged')

        self.make_hash_dict()
        self.task_hash = self.get_hash()

        #To Do: Merge outputs of map
        merge_map = {}
        for iter in outs:
            for k,v in iter.items():
                if k not in merge_map:
                    merge_map[k] = [v]
                else:
                    merge_map[k].extend([v])

        outs = tuple([[r.load() for r in merge_map['{}->{}'.format(self.name,name)]] for name in self.output_names])
        
        return self._process_outputs(outs)

    def run(self, iteration=None):
        #self.make_hash_dict()
        self.task_hash = self.get_hash()
        self.cache_dir = Path(self.global_parameters['cache_path'],self.task_hash)
        self.export_dir = Path(self.global_parameters['output_path'],self.name)
        self.return_as_function = self.parameters.get('return_as_function',False)
        self.return_as_class = self.parameters.get('return_as_class',False)
        self.logger.info('{}: Hash {}'.format(self.name,self.task_hash))
        
        cache_paths = self.find_cache()
        if self.cache and cache_paths:
            self.logger.info('{}: Caching'.format(self.name))
            out_dict = {'{}{}{}'.format(self.name,symbols['dot'],Path(cache_i).stem): TaskIO(cache_i,self.task_hash,iotype='path',name=Path(cache_i).stem,position=str(self.output_names.index(Path(cache_i).stem))) for cache_i in cache_paths}
            for task_name, task in out_dict.items():
                task.create_link(Path(task.data).parent,self.global_parameters['output_path'])
        else:
            run_async = self.parameters.get('async',False)
            if self.return_as_function:
                self.logger.info('{}: Lazy run'.format(self.name))
                self.parameters['return_as_function'] = False
                out_dict = self._process_outputs(self.process)
            elif self.return_as_class:
                self.logger.info('{}: Lazy run'.format(self.name))
                self.parameters['return_as_class'] = False
                out_dict = self._process_outputs(self)
            elif (('parallel' not in self.parameters) and ('map_vars' not in self.parameters)):
                self.logger.info('{}: Running'.format(self.name))
                out_dict = self._serial_run(run_async=run_async)
            elif 'parallel' in self.parameters and not 'map_vars' in self.parameters:
                self.logger.info('{}: Running with pool of {} workers'.format(self.name, self.parameters['n_cores']))
                out_dict = self._parallel_run_ray(run_async=run_async)
            elif 'map_vars' in self.parameters and not 'parallel' in self.parameters:
                if iteration is not None:
                    self.logger.info('{}: Running iteration {}'.format(self.name, iteration))
                else:
                    self.logger.info('{}: Running multiple iterations'.format(self.name))
                out_dict = self._serial_map(iteration=iteration,run_async=run_async)
            else:
                raise Exception('Mixing !parallel-map and !map in a task is not allowed')

        return out_dict

    
    def __getstate__(self):
        embed()
    
    def __setstate__(self,d):
        embed()

class TaskGraph(Task):
    def __init__(self,parameters,global_parameters=None, name=None, logger=None):
        super().__init__(parameters,global_parameters,name,logger)
        #Gather modules:
        self.external_modules = self.parameters.get('modules',[])
        self.external_modules = self.external_modules + self.global_parameters.get('modules',[])
        self.target = self.parameters.get('target',None)

        self.load_modules()
        #Build the graph
        self.graph = nx.DiGraph()
        self.gather_tasks()
        self.connect_tasks()
        #Get tasks execution order
        self.get_dependency_order()

    def send_dependency_data(self,data,ignore_map=False):
        #Override task method so that in this case, data keeps being a TaskIO
        for k,v in data.items():
            paths = self.hash_dict.find_path(k,action=lambda x: v.get_hash())
            if len(paths) > 0:
                self.parameters.find_path(k,action=lambda x: v)

    def load_modules(self):
        self.task_modules = get_modules(self.external_modules)

    def gather_tasks(self):
        """
        Here, all the tasks in config are instantiated and added as nodes to a nx graph
        """
        self.task_nodes = {}
        for task_name, task_config in self.parameters['Tasks'].items():
            task_class = task_config['class']
            if task_class == 'TaskGraph':
                task_obj = TaskGraph
                task_modules = task_config.get('modules',None)
                if task_modules is None:
                    task_config['modules'] = self.parameters['modules']
            else:
                task_obj = [getattr(module,task_class) for module in self.task_modules if task_class in get_classes_in_module(module)]
                if len(task_obj) == 0:
                    raise Exception('{} not recognized as a task'.format(task_class))
                elif len(task_obj) > 1:
                    raise Exception('{} found in multiple task modules. Rename the task in your module to avoid name collisions'.format(task_class))
                task_obj = task_obj[0]

            #run_async = task_config.get('async',False)
            #if run_async:
            #task_instance = ActorWrapper(copy.deepcopy(task_config),self.global_parameters,task_name,self.logger,actor = task_obj)
            #else:
            task_instance = task_obj(copy.deepcopy(task_config),self.global_parameters,task_name,self.logger)
            
            self.task_nodes[task_name] = task_instance

    def connect_tasks(self):
        """
        Here, edges are created using the dependencies variable from each task
        """
        self.graph = make_graph_from_tasks(self.task_nodes)

    def get_dependency_order(self):
        """
        Use topological sort to get the order of execution. If a target task is specified, find the shortest path.
        """
        if len(self.graph.nodes) == 0 and len(self.task_nodes)>0:
            self.dependency_order = [task for task_name, task in self.task_nodes.items()]
        else:
            self.dependency_order = list(nx.topological_sort(self.graph))

        if self.target:
            #Si tengo que ejecutar el DAG hasta cierto nodo, primero me fijo que nodo es:
            target_node = [node for node in self.dependency_order if node.name == self.target][0]
            target_idx = self.dependency_order.index(target_node)
            #Despues trunco la lista hasta el nodo, con esto estaria sacando todas las tareas que se iban a ejecutar despues:
            self.dependency_order = self.dependency_order[:target_idx+1]
            #Con esto puedo armar otro grafo que solo contenga los nodos que se iban a ejecutar antes que target.
            reduced_task_nodes = {node.name: node for node in self.dependency_order}
            pruned_graph = make_graph_from_tasks(reduced_task_nodes)
            #Es posible que algunas tareas se ejecutaran antes que target pero que no fueran necesarias para target sino que para un nodo posterior.
            #Estas tareas quedarian desconectadas del target. Busco los subgrafos conectados:
            connected_subgraphs = list(nx.components.connected_component_subgraphs(pruned_graph.to_undirected()))
            #Si hay mas de uno es porque quedaron tareas que no llevan a ningun lado. Agarro el subgrafo con la tarea target:
            if len(connected_subgraphs)>1:
                reachable_subgraph = [g for g in connected_subgraphs if target_node in g.nodes][0]
            else:
                reachable_subgraph = connected_subgraphs[0]
            #Armo el grafo de nuevo porque el algoritmo de subgrafos conectados necesita que sea un UAG.
            reduced_task_nodes = {node.name: node for node in reachable_subgraph.nodes}
            pruned_graph = make_graph_from_tasks(reduced_task_nodes)
            #Topological sort del grafo resultante me da las dependencias para el target task:
            self.dependency_order = list(nx.topological_sort(pruned_graph))
            self.graph = pruned_graph

        priority_nodes = [node for node in self.graph.nodes if 'priorize' in node.parameters and node.parameters['priorize']]
        
        if len(priority_nodes)>0:
            all_sorts = [top for top in nx.all_topological_sorts(self.graph)]
            sort_score = np.array([sum([top.index(pnode) for pnode in priority_nodes]) for top in all_sorts])
            best_sort = all_sorts[np.argmin(sort_score)]

            self.dependency_order = best_sort

    def _clear_tasksio_not_needed(self, remaining_tasks):
        needed_tasks = [list(self.graph.predecessors(node)) for node in self.graph.nodes if node.name in remaining_tasks]
        needed_tasks = [task.name for predecessors in needed_tasks for task in predecessors]

        tasks_io = copy.deepcopy(self.tasks_io)
        for io_name,io_value in tasks_io.items():
            task_producer = io_name.split(symbols['dot'])[0]
            if task_producer not in needed_tasks:
                self.tasks_io.pop(io_name)

    def process(self,params=None):
        if params is not None:
            self.parameters.update(params)
        """
        Runs each task in order, gather outputs and inputs.
        """

        remaining_tasks = [task.name for task in self.dependency_order]
        
        self.tasks_io = {}

        inputs = self.parameters.get('in',None)
        if inputs:
            for k,v in inputs.items():
                self.tasks_io['self->{}'.format(k)] = v
            #self.send_dependency_data(self.tasks_io,ignore_map=True)
        for task in self.dependency_order:
            
            task.reset_task_state()
            
            if 'iter' in self.parameters:
                task.parameters['iter'] = self.parameters['iter']
            task.export_path = Path(self.export_path,task.export_path.parts[-1])

            task.send_dependency_data(self.tasks_io)
            out_dict = task.run()

            self.tasks_io.update(out_dict)
            remaining_tasks.remove(task.name)
            #self._clear_tasksio_not_needed(remaining_tasks)

        filter_outputs = self.parameters.get('outputs',None)
        task_out = []
        
        if filter_outputs:
            self.output_names = []
            for k,v in filter_outputs.items():
                self.output_names.append(k)
                task_out.append(self.tasks_io[v].load())
            print('filter outputs')
            return tuple(task_out)
        else:
            #task_out = [self.tasks_io]
            return {}

    def __getstate__(self):
        if 'task_modules' in self.__dict__:
            del self.__dict__['task_modules']

        return self.__dict__

    def __setstate__(self,d):
        if 'external_modules' in d:
            task_modules = get_modules(d['external_modules'])
            d['task_modules'] = task_modules

        self.__dict__ = d
    




    