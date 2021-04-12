import os
import pickle
from pathlib import Path
from ruamel_yaml import YAML
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
from .file import *

from kahnfigh import Config
                
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