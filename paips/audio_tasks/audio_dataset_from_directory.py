from core import Task
import glob
from IPython import embed
from pathlib import Path
from pymediainfo import MediaInfo
import tqdm
import pandas as pd

class AudioDatasetFromDirectory(Task):
	def process(self):
		files = []
		for file in tqdm.tqdm(Path(self.parameters['dataset_path']).rglob('*.wav')):
			file_dict = {}
			stem_col = self.parameters.get('stem_as_column',None)
			dir_col = self.parameters.get('parents_as_columns',None)
			audio_info_fields = self.parameters.get('audio_info_fields',['sampling_rate','duration','samples_count','channel_s'])
			if stem_col:
				file_dict[stem_col] = file.stem
			if dir_col:
				for i,level in enumerate(reversed(dir_col)):
					file_dict[level] = file.parts[-2-i]
			file_dict['filename'] = str(file.absolute())
			if audio_info_fields:
				info = MediaInfo.parse(str(file.absolute()))
				audiotrack = None
				for track in info.tracks:
					if track.track_type == 'Audio':
						audiotrack = track
						break

				for field in audio_info_fields:
					file_dict[field] = getattr(audiotrack,field)

			files.append(file_dict)

		return pd.DataFrame(files)