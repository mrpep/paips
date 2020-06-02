from paips import Task
import pandas as pd
from pathlib import Path
from IPython import embed

class TRUSTReader(Task):
    def __init__(self,config,global_config):
        super().__init__(config,global_config)
        self.dataframes_path = self.config['dataframes_path']
        self.features_file = self.config['features_file']
        self.inputs=[]
        self.outputs=['features','metadata','questions']
        self.required_kwargs=['dataframes_path','features_file']

    def operation(self):
        if not isinstance(self.features_file,list):
            self.features_file = [self.features_file]

        feat_dfs = []
        for feat_name in self.features_file:
            df_feat_i = pd.read_pickle(Path(self.dataframes_path, feat_name))
            features = df_feat_i.columns
            features_to_rename = [feat for feat in features if ('[' in feat or ']' in feat)]
            renaming_dict = {k:k.replace(']','').replace('[','_') for k in features_to_rename}
            df_feat_i = df_feat_i.rename(renaming_dict,axis=1)
            feat_dfs.append(df_feat_i)

        df_feat = pd.concat(feat_dfs)

        df_metadata = pd.read_pickle(Path(self.dataframes_path, 'metadata.pkl'))
        df_questions = pd.read_pickle(Path(self.dataframes_path, 'questions.pkl'))

        df_metadata = df_metadata.rename(columns={'audio_name': 'logid'})
        df_metadata = df_metadata.set_index('logid')
        df_questions = df_questions.set_index('id')

        return df_feat, df_metadata, df_questions