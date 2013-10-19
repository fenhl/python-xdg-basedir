import os
import os.path

__version__ = '0.2.0'

class _basedirfile:
    def __enter__(self):
        self.fobj = open(self.path, self.flags)
        return self.fobj
    
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.fobj.close()
            self.fobj = None
        else:
            return False
    
    def __init__(self, path, flags='r'):
        self.path = path
        self.flags = 'r'
    
    def __str__(self):
        return self.path

class _basedir:
    def __call__(self, filename, flags='r'):
        return _basedirfile(os.path.join(self.path, filename), flags=flags)
    
    def __init__(self, envar, default):
        dir = os.environ.get(envar)
        self.path = default if dir is None or dir == '' else dir
    
    def __str__(self):
        return self.path

class _basedirs:
    def __call__(self, filename, flags='r'):
        for dir in self:
            if os.path.exists(os.path.join(dir, filename)):
                return _basedirfile(os.path.join(dir, filename), flags=flags)
        else:
            raise IOError('file not found')
    
    def __init__(self, envar, default, home):
        self.home = home
        dirs_envar = os.environ.get(envar)
        self.paths = default if dirs_envar is None or dirs_envar == '' else ':'.split(dirs_envar)
    
    def __iter__(self):
        yield str(self.home)
        yield from self.paths
    
    def __str__(self, include_home=False):
        paths = ([str(self.home)] if include_home else []) + list(self.paths)
        return ':'.join(paths)

data_home = _basedir('XDG_DATA_HOME', os.path.join(os.environ['HOME'], '.local/share'))
config_home = _basedir('XDG_CONFIG_HOME', os.path.join(os.environ['HOME'], '.config'))
data_dirs = _basedirs('XDG_DATA_DIRS', ['/usr/local/share', '/usr/share'], data_home)
config_dirs = _basedirs('XDG_CONFIG_DIRS', ['/etc/xdg'], config_home)
