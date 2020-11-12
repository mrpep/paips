import glob
import hashlib
import json
from pathlib import Path

from IPython import embed
from swissknife.aws import S3File

def make_hash(hash_dict):
	hashable_str = str(json.dumps(hash_dict,sort_keys=True,default=str,ensure_ascii=True))
	task_hash = hashlib.sha1(hashable_str.encode('utf-8')).hexdigest()

	return task_hash

def find_cache(hash_val,cache_path):
	if cache_path.startswith('s3://'):
		s3_obj = S3File(cache_path,hash_val)

		#Maybe cache path was already downloaded from S3, in that case first look in locals
		cache_dir = Path(cache_path.split('s3://')[-1],hash_val)
		cache_dirs = glob.glob(str(cache_dir.absolute())+'_*/*')

		if len(cache_dirs)>0:
			return cache_dirs
		else:
			#If no cache found local, look in S3
			cache_dirs = s3_obj.glob(s3_obj.path+'_*/*')
			if len(cache_dirs)>0:
				return cache_dirs
			else:
				return None

	else:
		cache_dir = Path(cache_path,hash_val)
		cache_dirs = glob.glob(str(cache_dir.absolute())+'_*/*')

	if len(cache_dirs) > 0:
		return cache_dirs
	else:
		return None