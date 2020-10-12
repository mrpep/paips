import glob
import hashlib
import json
from pathlib import Path

def make_hash(hash_dict):
	hashable_str = str(json.dumps(hash_dict,sort_keys=True,default=str,ensure_ascii=True))
	task_hash = hashlib.sha1(hashable_str.encode('utf-8')).hexdigest()

	return task_hash

def find_cache(hash_val,cache_path):
	cache_dir = Path(cache_path,hash_val)
	cache_dirs = glob.glob(str(cache_dir.absolute())+'_*/*')
	if len(cache_dirs) > 0:
		return cache_dirs
	else:
		return None