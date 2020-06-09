import soundfile as sf
from deytah.core import Processor
import pandas as pd
from IPython import embed
import numpy as np

class Mixer2(Processor):
    def operation(self, audios, gain):
        audios = np.array(audios)
        if not isinstance(gain,list) or not isinstance(gain,np.ndarray):
            gain = gain*np.ones_like(audios)
        
        def func(audios, gain):
            return np.sum(gain*audios,axis=0)

        return pd.Series(map(func, audios, gain))