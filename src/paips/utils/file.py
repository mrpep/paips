from pyknife.aws import S3File
from pathlib import Path
import joblib

class GenericFile():
    def __init__(self,*args):
        args = [arg if isinstance(arg,str) else str(arg) for arg in args]
        if str(args[0]).startswith('s3:/'):
            self.filesystem = 's3'
            self.file_obj = S3File(*args)
            self.local_filename = str(Path(self.file_obj.get_key()))
            self.parent = Path(self.file_obj.get_key()).parent
        else:
            self.filesystem = 'local'
            self.file_obj = Path(*args)
            self.parent = self.file_obj.parent
            self.local_filename = str(Path(self.file_obj))

    def load(self):
        if self.filesystem == 's3':
            if not Path(self.local_filename).exists():
                self.file_obj.download(Path(self.file_obj.get_key()))
            return joblib.load(Path(self.file_obj.get_key()))
        elif self.filesystem == 'local':
            return joblib.load(self.file_obj)

    def download(self):
        if self.filesystem == 's3':
            self.file_obj.download(Path(self.file_obj.get_key()))

    def __str__(self):
        return str(self.file_obj)

    def upload_from(self, source):
        if self.filesystem == 's3':
            self.file_obj.upload(source)

    def exists(self):
        return self.file_obj.exists()

    def is_symlink(self):
        if self.filesystem == 's3':
            return Path(self.file_obj.get_key()).is_symlink()
        else:
            return self.file_obj.is_symlink()

    def unlink(self):
        Path(self.local_filename).unlink()

    def absolute(self):
        if self.filesystem == 's3':
            return Path(self.file_obj.get_key()).absolute()
        else:
            return self.file_obj.absolute()

    def mkdir(self,*args, **kwargs):
        if self.filesystem == 's3':
            dirpath = Path(self.file_obj.get_key())
            if not dirpath.exists():
                dirpath.mkdir(*args,**kwargs)
        else:
            if not self.file_obj.exists():
                self.file_obj.mkdir(*args,**kwargs)
