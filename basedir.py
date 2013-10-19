import json
import os
import os.path

__version__ = '0.4.0'

class _basedirfile:
    def __enter__(self):
        self.fobj = open(path, self.flags)
        return self.fobj
    
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.fobj.close()
            self.fobj = None
        else:
            try:
                self.fobj.close()
            finally:
                pass
            return False
    
    def __init__(self, paths, filename, flags='r'):
        self.paths = paths
        for path in self.paths:
            if os.path.exists(os.path.join(path, filename)):
                self.path = path
                break
        else:
            self.path = None
        self.filename = filename
        self.flags = 'r'
    
    def __str__(self):
        return ':'.join(os.path.join(path, self.filename) for path in self.paths)
    
    def json(self):
        def _patch_json(base, new):
            new_json = json.load(new)
            if type(new_json) is dict:
                if type(base) is not dict:
                    return new_json
                base.update(new_json)
                return base
            elif type(new_json) is list:
                if type(base) is not list:
                    return new_json
                return base + new_json
            else:
                return new_json
        
        return self.read(patch=_patch_json)
    
    def read(self, patch=None):
        """If patch is None (the default), this returns the contents of the first found file.
        
        If patch is not None, it must be a function of the form patch(base, new). This function will then read all existing files in reverse order, and call the patch function with the results of the last call (or None for the first call) as the first argument, and a file object representing the current file as the second argument. The end result is returned.
        """
        if patch is None:
            for path in self.paths:
                if os.path.exists(os.path.join(path, self.filename)):
                    with open(os.path.join(path, self.filename)) as f:
                        return f.read()
        else:
            base = None
            for path in reversed(self.paths):
                if os.path.exists(os.path.join(path, self.filename)):
                    with open(os.path.join(path, self.filename)) as new:
                        base = patch(base, new)
            return base

class _basedir:
    def __call__(self, filename, flags='r'):
        return _basedirfile([self.path], filename, flags=flags)
    
    def __init__(self, envar, default):
        dir = os.environ.get(envar)
        self.path = default if dir is None or dir == '' else dir
    
    def __str__(self):
        return self.path

class _basedirs:
    def __call__(self, filename, flags='r'):
        return _basedirfile(self.paths, filename, flags=flags)
    
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
