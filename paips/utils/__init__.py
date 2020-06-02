import os
import pickle
from pathlib import Path
from ruamel.yaml import YAML
from IPython import embed
import importlib
import sys
import inspect

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

def module_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def module_from_folder(module_path):
    """
    Arguments:
        module_path: path to a .py file
    Returns:
        the module in module_path
    """

    module_path = Path(module_path)
    sys.path.append(str((module_path.absolute()).parent))
    module = importlib.import_module(module_path.stem)

    return module

def get_classes_in_module(module):
    """
    Returns a dictionary containing all the available classes in a module.
    Arguments:
        module: a module from which to extract available classes
    Outputs:
        returns a dictionary containing class names as keys and class objects as values. 
    """

    clsmembers = inspect.getmembers(module, inspect.isclass)
    clsmembers_dict = {cls[0]:cls[1] for cls in clsmembers}

    return clsmembers_dict