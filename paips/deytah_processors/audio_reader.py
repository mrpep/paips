import numpy as np
import pandas as pd
import soundfile as sf
from deytah.core import Processor
import pandas as pd
from IPython import embed
import librosa

class MultiAudioReader(Processor):
    def operation(self, filename, start, end, sr):
        def func(filename, start, end, sr):
            outs = [sf.read(filename_i,start=start_i,stop=end_i)[0] for filename_i,start_i,end_i in zip(filename,start,end)]
            return outs

        return pd.Series(map(func, filename, start, end, sr))