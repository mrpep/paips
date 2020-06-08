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
	if cache_dir.exists():
		return glob.glob(str(cache_dir.absolute())+'/*')
	else:
		return None