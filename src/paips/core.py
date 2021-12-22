from .utils.config_processors import (get_delete_param, apply_mods)
from .utils.nested import (search_replace, search_dependencies)
from .utils.cache import find_cache
from .utils.graphs import make_graph_from_tasks
from .utils.modiuls import (get_modules, get_classes_in_module)
from .utils.file import GenericFile
from .utils.settings import symbols

import copy
import numpy as np
import joblib
from pathlib import Path
import networkx as nx
from kahnfigh import Config
from kahnfigh.core import find_path
try:
    from ruamel.yaml import YAML
except:
    from ruamel_yaml import YAML
import os

from shutil import copyfile
import glob
import fnmatch

import time

from pyknife.aws import get_instances_info

class TaskIO():
    """
    A class to store the inputs and outputs for each task.
    """
    def __init__(self, data, hash_val, iotype = 'data', name = None,position='0'):
        """
        data: data to be stored
        hash_val: hash of the task that generated the data
        iotype: can be 'data' or 'path' depending on if it already exists and it is saved in disk
        name: name of the output. It is the name the file will have when saved in cache or exported
        position: it is used to differentiate multiple outputs of a task. It gets appended to the hash (<hash_val>_<position>)
        """

        self.hash = hash_val
        self.data = data
        self.iotype = iotype
        self.name = name
        self.link_path = None
        if position:
            self.hash = self.hash + '_{}'.format(position)

    def get_hash(self):
        return self.hash

    def load(self):
        if self.iotype == 'data':
            return self.data
        elif self.iotype == 'path':
            return GenericFile(self.data).load()

    def save(self, cache_path=None, export_path=None, compression_level = 0, export=False,symlink_db=None,overwrite_export=True):
        """
        cache_path: it is where the data will be saved
        export_path: path more accessible and human-readable to store symbolic links to the cache files
        compression_level: >0 gets compressed, meaning less space in disk but slower access and write times
        export: if True, instead of having a symlink in the export_path, the cache file will get copied to export_path
        symlink_db: path to a file that will be created containing information about where each task output is
        overwrite_export: if export files already exist, they will get overwritten
        """
        self.address = GenericFile(cache_path,self.hash,self.name)
        if not self.address.parent.exists():
            self.address.parent.mkdir(parents=True)
            
        #Save cache locally:
        if Path(self.address.local_filename).exists():
            Path(self.address.local_filename).unlink()
        joblib.dump(self.data,self.address.local_filename,compress=compression_level)

        #Create symbolic link
        self.create_link(self.address.parent,export_path,copy_files=export,symlink_db=symlink_db,overwrite = overwrite_export)

        #If S3, also upload it
        if (self.address.filesystem == 's3') and not export:
            self.address.upload_from(self.address.local_filename)

        #Now TaskIO no longer stores data, but a path to the actual data
        return TaskIO(self.address,self.hash,iotype='path',name=self.name,position=None)

    def create_link(self, cache_path, export_path,copy_files=False,symlink_db=None,overwrite=True):
        cache_path = cache_path.absolute()
        source_file = glob.glob(str(cache_path)+'/*')
        #For each file in cache_path, create symlinks or export
        for f in source_file:
            destination_path = GenericFile(export_path,Path(f).stem)
            if not destination_path.parent.exists():
                destination_path.parent.mkdir(parents=True,exist_ok=True)
            if copy_files:
                # If we want easy access to files, then the real file will be at export path and the symlink in cache
                if (not destination_path.is_symlink() and not destination_path.exists()) or overwrite:
                    if Path(destination_path.local_filename).exists():
                        destination_path.unlink()
                    copyfile(f,str(destination_path.absolute()))
                    if destination_path.filesystem == 's3':
                        destination_path.upload_from(str(destination_path.absolute()))

                    if symlink_db is not None:
                        symlink_file = GenericFile(symlink_db)
                        if not Path(symlink_file.local_filename).exists() and symlink_file.exists():
                            symlink_file.download()
                        with open(str(symlink_file.local_filename),'a+') as fw:
                            fw.write('{} -> {}\n'.format(f,str(destination_path)))
                        if symlink_file.filesystem == 's3':
                            symlink_file.upload_from(str(symlink_file.local_filename))
            else:
                #Just create a symlink
                if not destination_path.is_symlink() and not destination_path.exists():
                    os.symlink(f,str(destination_path.absolute()))

                    if symlink_db is not None:
                        symlink_file = GenericFile(symlink_db)
                        if not Path(symlink_file.local_filename).exists() and symlink_file.exists():
                            symlink_file.download()
                        with open(symlink_file.local_filename,'a+') as fw:
                            fw.write('{} -> {}\n'.format(str(destination_path),f))
                        if symlink_file.filesystem == 's3':
                            symlink_file.upload_from(symlink_file.local_filename)

    def __getstate__(self):
        return self.__dict__
    
    def __setstate__(self,d):
        self.__dict__ = d

class Task():
    def __init__(self, parameters, global_parameters=None, name=None, logger=None, simulate=False):
        """
        parameters: dictionary with all parameters given to a task
        global_parameters: dictionary with parameters common to all tasks
        name: task name
        logger: task logger
        simulate: if True, the task won't get executed
        """
        self.global_parameters = {'cache': True,
                             'cache_path': 'cache',
                             'cache_compression': 0,
                             'output_path': 'experiments',
                             'overwrite_export': True}

        if global_parameters:
            self.global_parameters.update(global_parameters)

        if not GenericFile(self.global_parameters['output_path']).exists():
            GenericFile(self.global_parameters['output_path']).mkdir(parents=True)

        self.name = name
        self.valid_args=[]
        self.default_no_cache: []

        self.parameters = parameters

        self.simulate = simulate

        self.output_names = self.parameters.pop('output_names',['out'])
        self.cache = get_delete_param(self.parameters,'cache',self.global_parameters['cache'])
        self.in_memory = get_delete_param(self.parameters,'in_memory',self.global_parameters['in_memory'])

        self.dependencies = []
        self.logger = logger

        if 'mods' in self.parameters:
            apply_mods(self.parameters['mods'],Config(self.parameters))
            self.parameters.pop('mods')

        self.__make_hash_dict()
        self.initial_parameters = copy.deepcopy(self.parameters)

        self.export_path = Path(self.global_parameters.get('output_path'),self.name)
        self.export = self.parameters.get('export',False)
        self.symlinkdb_path = Path(self.global_parameters.get('output_path'),'links.txt')

        fname = GenericFile(self.global_parameters['output_path'],'configs','{}.yaml'.format(self.name))
        self.parameters.save(Path(fname.local_filename), mode='unsafe')
        if fname.filesystem == 's3':
            fname.upload_from(fname.local_filename)

    def __make_hash_dict(self):
        """
        Creates a dictionary to hash the task. Parameters that are TaskIOs get replaced by their hash
        """
        self._hash_dict = copy.deepcopy(self.parameters)
        #Remove not cacheable parameters
        if not isinstance(self._hash_dict, Config):
            self._hash_dict = Config(self._hash_dict)
        if not isinstance(self.parameters, Config):
            self.parameters = Config(self.parameters)

        _ = self._hash_dict.find_path(symbols['nocache'],mode='startswith',action='remove_value')
        _ = self.parameters.find_path(symbols['nocache'],mode='startswith',action='remove_substring')

        for k,v in self._hash_dict.to_shallow().items():
            if isinstance(v,TaskIO):
                self._hash_dict[k] = self._hash_dict[k].get_hash()

    def search_dependencies(self):
        """
        Finds all the tasks needed to run this task. It does it by searching for the -> symbol in its config
        """
        stop_propagate_dot = self.parameters.get('stop_propagate_dot',None)
        dependency_paths = self.parameters.find_path(symbols['dot'],mode='contains')
        #dependency_paths = [p for p in dependency_paths if 'Tasks' not in ]
        if self.__class__.__name__ == 'TaskGraph':
            dependency_paths = [p for p in dependency_paths if ('Tasks' not in p) and (not p.startswith('outputs'))]
        #Esto es porque dienen tambien usa el simbolo -> entonces debo decir que si encuentra ahi no lo tenga en cuenta.
        if stop_propagate_dot:
            dependency_paths = [p for p in dependency_paths if not p.startswith(stop_propagate_dot)]

        self._dependencies = [self.parameters[path].split(symbols['dot'])[0] for path in dependency_paths]
        self._dependencies = [d for d in self._dependencies if d != 'self']

        return self._dependencies

    def reset_task_state(self):
        """
        Returns the task to its initial parameters and hash_dict
        """
        self.parameters = copy.deepcopy(self.initial_parameters)
        self.__make_hash_dict()

    def __check_valid_args(self):
        """
        Each task can have a valid_args list which lists the allowed parameters
        """
        for k in self.parameters.keys():
            if k not in self.valid_args:
                raise Exception('{} not recognized as a valid parameter'.format(k))

    def send_dependency_data(self,data):
        """
        Replace TaskIOs in parameters with the corresponding data. Also adds its associated hashes to the hash dictionary
        """
        glob_keys = self.parameters.find_path('*',mode='contains',action=lambda x: fnmatch.filter(list(data.keys()),x) if '->' in x else x)
        glob_keys = self._hash_dict.find_path('*',mode='contains',action=lambda x: fnmatch.filter(list(data.keys()),x) if '->' in x else x)
        
        for k,v in data.items():
            paths = self._hash_dict.find_path(k,action=lambda x: v.get_hash())
            if len(paths) > 0:
                self.parameters.find_path(k,action=lambda x: v.load())
            else:
                if self.simulate and not k.startswith('self'):
                    k_ = k.split('->')[0]+'->'
                    paths = self._hash_dict.find_path(k_,action=lambda x: v.get_hash(),mode='startswith')

    def get_hash(self):
        """
        Returns an unique identifier for the task
        """
        task_hash =  self.parameters.get('task_hash',None)
        if task_hash is None:
            return self._hash_dict.hash()
        else:
            return task_hash
        
    def process(self):
        pass

    def find_cache(self):
        """
        Finds all the associated files in cache
        """
        cache_paths = find_cache(self.task_hash,self.global_parameters['cache_path'])
        return cache_paths

    def __process_outputs(self,outs):
        """
        Task outputs are turned into TaskIOs and saved if in_memory = False. All outputs TaskIO are returned in a dictionary.
        """
        if type(outs).__name__ == 'ObjectRef':
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
                        export=self.export,
                        symlink_db=self.symlinkdb_path,
                        overwrite_export=self.global_parameters['overwrite_export'])

        return out_dict

    def __parallel_run_ray(self,run_async = False):
        """
        Initializes a ray pool. Asynchronous pools are still not implemented.
        """
        from ray.util.multiprocessing.pool import Pool

        def set_niceness(niceness): # pool initializer
            os.nice(niceness)

        def worker_wrapper(x):
            os.nice(self.parameters.get('niceness',20))
            for k, v in zip(self.parameters['parallel'],x):
                self.parameters[k] = v
            out = self.process()
            return out

        iterable_vars = list(zip(*[self.parameters[k] for k in self.parameters['parallel']]))
        n_cores = self.parameters.get('n_cores',4)
        pool = Pool(processes=n_cores, initializer=set_niceness,initargs=(self.parameters.get('niceness',20),),ray_address='auto') #(Run in same host it was called)
        outs = pool.map(worker_wrapper,iterable_vars)

        return self.__process_outputs(outs)

    def __serial_run(self,run_async=False):
        """
        Run the task. Can be ran asynchronously using ray, and custom resources can be assigned through 'resources' parameter.
        """
        if run_async:
            import ray
            import os
            import sys

            def run_process_async(self):
                os.nice(self.parameters.get('niceness',20))
                self.logger.info('{}: Setting niceness {}'.format(self.name, self.parameters.get('niceness',20)))
                return self.process()

            resource_settings = self.parameters.get('resources',None)
            if resource_settings and 'gpus' in resource_settings:
                num_gpus = resource_settings['gpus']
                resource_settings.pop('gpus')
            else:
                num_gpus = 0
                
            if resource_settings:
                outs = ray.remote(run_process_async)._remote(args=[self],resources=resource_settings, num_gpus=num_gpus)
            else:
                outs = ray.remote(run_process_async).remote(self)
        else:
            outs = self.process()
        return self.__process_outputs(outs)

    def __serial_map(self,iteration=None,run_async=False):
        """
        Run the task over each input element. Can be ran asynchronously.
        """
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
            self.cache_dir = Path(self.global_parameters['cache_path'],self.task_hash)
            self.export_path = Path(self.original_export_path,str(i))

            self.__make_hash_dict()
            self.task_hash = self.get_hash()

            for k, var in zip(map_var_names,iteration):
                self.parameters[k] = TaskIO(var,self.task_hash,iotype='data',name=k)

            if self.cache:
                cache_paths = self.find_cache()
            else:
                cache_paths = False
            if cache_paths:
                self.logger.info('Caching task {}'.format(self.name))
                out_dict = {'{}{}{}'.format(self.name,symbols['dot'],Path(cache_i).stem): TaskIO(cache_i,self.task_hash,iotype='path',name=Path(cache_i).stem,position=Path(cache_i).parts[-2].split('_')[-1]) for cache_i in cache_paths}
                for task_name, task in out_dict.items():
                    task.create_link(Path(task.data).parent,Path(self.export_path))
            elif run_async:
                outs.append({'{}->ray_reference'.format(self.name): list(self.__serial_run(run_async=run_async).values())[0],
                       '{}->output_names'.format(self.name): TaskIO(self.output_names,self.get_hash(),iotype='data',name='output_names',position='1')})
                self.output_names = ['ray_reference','output_names']
            else:
                outs.append(self.__serial_run(run_async=run_async))
            print('serial map')

        #Restore original parameters
        self.parameters = copy.deepcopy(self.initial_parameters)
        self.name = copy.deepcopy(self.original_name)
        self.export_path = Path(self.original_export_path,'merged')

        self.__make_hash_dict()
        self.task_hash = self.get_hash()

        merge_map = {}
        for iter in outs:
            for k,v in iter.items():
                if k not in merge_map:
                    merge_map[k] = [v]
                else:
                    merge_map[k].extend([v])

        outs = tuple([[r.load() for r in merge_map['{}->{}'.format(self.name,name)]] for name in self.output_names])
        
        return self.__process_outputs(outs)

    def run(self, iteration=None):
        """
        The task is ran. If it is doing a map over the inputs, then iteration is given.
        Handles the different behaviours like return_as_class/function, map and parallel.
        """
        self.task_hash = self.get_hash()
        self.cache_dir = Path(self.global_parameters['cache_path'],self.task_hash)
        self.export_dir = Path(self.global_parameters['output_path'],self.name)
        
        self.return_as_function = self.parameters.get('return_as_function',False)
        self.return_as_class = self.parameters.get('return_as_class',False)
        if self.logger is not None:
            self.logger.info('{}: Hash {}'.format(self.name,self.task_hash))
        
        if self.cache:
            cache_paths = self.find_cache()
        else:
            cache_paths = False
        if cache_paths:
            if self.logger is not None:
                self.logger.info('{}: Caching'.format(self.name))

            out_dict = {'{}{}{}'.format(self.name,symbols['dot'],Path(cache_i).stem): TaskIO(cache_i,self.task_hash,iotype='path',name=Path(cache_i).stem,position=Path(cache_i).parts[-2].split('_')[-1]) for cache_i in cache_paths}
            for task_name, task in out_dict.items():
                export = self.parameters.get('export', False)
                task.create_link(Path(task.data).parent,Path(self.export_path),copy_files=export)
        else:
            run_async = self.parameters.get('async',False)
            if self.return_as_function:
                if self.logger is not None:
                    self.logger.info('{}: Lazy run'.format(self.name))
                self.parameters['return_as_function'] = False
                out_dict = self.__process_outputs(self.process)
            elif self.return_as_class:
                if self.logger is not None:
                    self.logger.info('{}: Lazy run'.format(self.name))
                self.parameters['return_as_class'] = False
                out_dict = self.__process_outputs(self)
            elif (('parallel' not in self.parameters) and ('map_vars' not in self.parameters)):
                if self.logger is not None:
                    self.logger.info('{}: Running'.format(self.name))
                out_dict = self.__serial_run(run_async=run_async)
            elif 'parallel' in self.parameters and not 'map_vars' in self.parameters:
                if self.logger is not None:
                    self.logger.info('{}: Running with pool of {} workers'.format(self.name, self.parameters['n_cores']))
                out_dict = self.__parallel_run_ray(run_async=run_async)
            elif 'map_vars' in self.parameters and not 'parallel' in self.parameters:
                if iteration is not None:
                    if self.logger is not None:
                        self.logger.info('{}: Running iteration {}'.format(self.name, iteration))
                else:
                    if self.logger is not None:
                        self.logger.info('{}: Running multiple iterations'.format(self.name))
                out_dict = self.__serial_map(iteration=iteration,run_async=run_async)
            else:
                raise Exception('Mixing !parallel-map and !map in a task is not allowed')

        return out_dict

class TaskGraph(Task):
    """
    This is the most important Task, which executes the pipeline. It can be included inside another pipeline (nested pipelines)
    """
    def __init__(self,parameters,global_parameters=None, name=None, logger=None, simulate=False):
        """
        args have the same meaning as in Task
        """
        if not parameters.get('logging',True):
            logger = None
        super().__init__(parameters,global_parameters,name,logger)
        #Gather modules:
        self._external_modules = self.parameters.get('modules',[])
        self._external_modules = self._external_modules + self.global_parameters.get('modules',[])
        self.target = self.parameters.get('target',None)
        self.simulate = simulate

        self.__load_modules()
        #Build the graph
        self._graph = nx.DiGraph()
        if self.logger is not None:
            self.logger.info('Gathering tasks for {}'.format(self.name))
        self.__gather_tasks()
        self.__connect_tasks()
        #Get tasks execution order
        self.__get_dependency_order()

    def send_dependency_data(self,data,ignore_map=False):
        #Override task method so that in this case, data keeps being a TaskIO
        glob_keys = self.parameters.find_path('*',mode='contains',action=lambda x: fnmatch.filter(list(data.keys()),x) if '->' in x else x)
        glob_keys = self._hash_dict.find_path('*',mode='contains',action=lambda x: fnmatch.filter(list(data.keys()),x) if '->' in x else x)

        for k,v in data.items():
            paths = self._hash_dict.find_path(k,action=lambda x: v.get_hash())
            if len(paths) > 0:
                self.parameters.find_path(k,action=lambda x: v)

    def __load_modules(self):
        self.task_modules = get_modules(self._external_modules)

    def __gather_tasks(self):
        """
        Here, all the tasks in config are instantiated and added as nodes to a nx graph
        """
        self._task_nodes = {}
        for task_name, task_config in self.parameters['Tasks'].items():
            if 'class' in task_config:
                task_class = task_config['class']
            else:
                raise Exception('class parameter missing in task {}'.format(task_name))
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

            task_instance = task_obj(copy.deepcopy(task_config),self.global_parameters,task_name,self.logger)
            
            self._task_nodes[task_name] = task_instance

    def __connect_tasks(self):
        """
        Here, edges are created using the dependencies variable from each task
        """
        self._graph = make_graph_from_tasks(self._task_nodes)

    def __get_dependency_order(self):
        """
        Use topological sort to get the order of execution. If a target task is specified, find the shortest path.
        """
        if len(self._graph.nodes) == 0 and len(self._task_nodes)>0:
            self._dependency_order = [task for task_name, task in self._task_nodes.items()]
        else:
            self._dependency_order = list(nx.topological_sort(self._graph))

        if self.target:
            #Si tengo que ejecutar el DAG hasta cierto nodo, primero me fijo que nodo es:
            target_node = [node for node in self._dependency_order if node.name == self.target][0]
            target_idx = self._dependency_order.index(target_node)
            #Despues trunco la lista hasta el nodo, con esto estaria sacando todas las tareas que se iban a ejecutar despues:
            self._dependency_order = self._dependency_order[:target_idx+1]
            #Con esto puedo armar otro grafo que solo contenga los nodos que se iban a ejecutar antes que target.
            reduced_task_nodes = {node.name: node for node in self._dependency_order}
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
            self._dependency_order = list(nx.topological_sort(pruned_graph))
            self._graph = pruned_graph

        priority_nodes = [node for node in self._graph.nodes if 'priorize' in node.parameters and node.parameters['priorize']]
        
        if len(priority_nodes)>0:
            #This can be improved, instead of searching all topological_sorts, we could just use one and keep track of all the
            #tasks that can be executed at any moment. If one of those tasks has priorize, then run it first.
            import itertools
            all_sorts = [top for top in itertools.islice(nx.all_topological_sorts(self._graph),100)]
            sort_score = np.array([sum([top.index(pnode) for pnode in priority_nodes]) for top in all_sorts])
            best_sort = all_sorts[np.argmin(sort_score)]

            self._dependency_order = best_sort

        for node in self._graph.nodes:
            if node.parameters.get('run_first',False):
                self._dependency_order.remove(node)
                self._dependency_order.insert(0,node)

    def __clear_tasksio_not_needed(self, remaining_tasks):
        needed_tasks = [list(self._graph.predecessors(node)) for node in self._graph.nodes if node.name in remaining_tasks]
        needed_tasks = [task.name for predecessors in needed_tasks for task in predecessors]

        tasks_io = copy.deepcopy(self.tasks_io)
        for io_name,io_value in tasks_io.items():
            task_producer = io_name.split(symbols['dot'])[0]
            if task_producer not in needed_tasks:
                self.tasks_io.pop(io_name)

    def process(self,params=None):
        """
        Runs each task in order, gather outputs and inputs.
        """

        if params is not None:
            self.parameters.update(params)
        remaining_tasks = [task.name for task in self._dependency_order]
        run_from = self.parameters.get('run_from',None)
        also_run = self.parameters.get('also_run',None)
        if run_from:
            idx_run_from = remaining_tasks.index(run_from)
            runnable_tasks = remaining_tasks[idx_run_from:]
            if also_run:
                if not isinstance(also_run,list):
                    also_run = [also_run]
                runnable_tasks = runnable_tasks + also_run
        else:
            runnable_tasks = copy.deepcopy(remaining_tasks)

        self.tasks_io = {}

        inputs = self.parameters.get('in',None)
        if inputs:
            for k,v in inputs.items():
                self.tasks_io['self->{}'.format(k)] = v

        for task in self._dependency_order:
            task.reset_task_state()
            
            if 'iter' in self.parameters:
                task.parameters['iter'] = self.parameters['iter']
            task.export_path = Path(self.export_path,task.export_path.parts[-1])

            task.send_dependency_data(self.tasks_io)
            if task.parameters['class'] == 'WANDBExperiment':
                task.config = self.parameters.to_shallow()
            if task.name not in runnable_tasks or self.simulate:
                if task.parameters['class'] == 'TaskGraph':
                    task.simulate = True
                    out_dict = task.run()
                else:
                    if self.logger is not None:
                        self.logger.info('Skipping {}'.format(task.name))
                    outs = [None for out in task.output_names]
                    out_dict = {'{}{}{}'.format(task.name,symbols['dot'],out_name): TaskIO(out_val,task.get_hash(),iotype='data',name=out_name,position=str(i)) for i, (out_name, out_val) in enumerate(zip(task.output_names,outs))}
            else:
                start_time = time.time()
                out_dict = task.run()
                if self.logger is not None:
                    self.logger.info('Elapsed {:.4f} seconds.'.format(time.time() - start_time))

            self.tasks_io.update(out_dict)
            remaining_tasks.remove(task.name)

        filter_outputs = self.parameters.get('outputs',None)
        task_out = []
        
        if filter_outputs:
            self.output_names = []
            for k,v in filter_outputs.items():
                self.output_names.append(k)
                task_out.append(self.tasks_io[v].load())           
            return tuple(task_out)
        else:
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
    




    