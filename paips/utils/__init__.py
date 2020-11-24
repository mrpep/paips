import os
import pickle
from pathlib import Path
from ruamel.yaml import YAML
import importlib
import sys
import inspect
from io import StringIO

from .modiuls import *
from .nested import *
from .cache import *
from .graphs import *
from .settings import symbols
from .diagnose import *
from .distributed import *
from .file import *

def apply_mods(modstr,config):
    
    yaml = YAML()
    if modstr is not None:
        mods = modstr.split('&')
        for mod in mods:
            if '=' in mod:
                mod_parts = mod.split('=')
                #if mod_parts[1].startswith('['):
                if '!' in mod_parts[1]:
                    config[mod_parts[0]] = mod_parts[1]
                #elif mod_parts[1].lower() == 'null':
                #    config[mod_parts[0]] = None
                else:
                    config[mod_parts[0]] = yaml.load(mod_parts[1])
                
                    

def get_delete_param(dictionary,param,default_value=None):
    if param in dictionary:
        return dictionary.pop(param)
    else:
        return default_value

def load_pickle(path):
    with open(path, 'rb') as fp:
        return pickle.load(fp)


def dump_pickle(obj, path):
    with open(path, 'wb') as fp:
        return pickle.dump(obj, fp)


def load_or_dump(obj, path, cache=False):
    if path.exists() and cache:
        return load_pickle(path)
    else:
        Path(path.parent).mkdir(parents=True, exist_ok=True)
        dump_pickle(obj, path)
        return obj

def get_config(filename):
    yaml = YAML(typ='safe')
    config = yaml.load(Path(filename))
    return config

def save_config(config,filename):
    yaml = YAML(typ='safe')
    yaml.dump(config,Path(filename))

def get_labels_from_deytah(filename):
    if filename:
        yaml = YAML(typ='safe')
        config = yaml.load(Path(filename))
        if 'Processors' in config.keys():
            all_processors = config['Processors']
            for k, proc in all_processors.items():
                if proc['processor'] == 'LabelEncoder':
                    return proc['labels']
    return None

def get_run_output_path(config, output_path, overwrite=True):
    run_output_path = Path(output_path, config['name'])
    if run_output_path.exists():
        if not overwrite:
            raise Exception('Directory {} already exist'.format(run_output_path))
    else:
        run_output_path.mkdir(parents=True)
    return run_output_path

def assert_config(config):
    assert 'experiment_name' in config.keys()

def copy_config(config_path, output_dir, name=None):
    if name is None:
        name = "config"
    copy_path = str(Path(output_dir, name).with_suffix(".yaml"))
    shutil.copy(config_path, copy_path)