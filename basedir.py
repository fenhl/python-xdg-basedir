import json
import os
import os.path

__version__ = '0.6.0'

try:
    import lazyjson
except ImportError:
    pass
else:
    class Config(lazyjson.File):
        def __init__(self, basedir_file):
            self.basedir_file = basedir_file
            self.file_info = os.path.join(self.basedir_file.path, self.basedir_file.filename)
        
        def value_at_key_path(self, key_path):
            found = False
            ret = None
            for json_path in reversed(self.basedir_file):
                with open(json_path) as json_file:
                    item = json.load(json_file)
                for key in key_path:
                    try:
                        item = item[key]
                    except (IndexError, KeyError):
                        break
                else:
                    found = True
                    if all(isinstance(key, str) for key in key_path) and isinstance(ret, dict) and isinstance(item, dict):
                        ret.update(item)
                    else:
                        ret = item
            if not found:
                raise KeyError()
            return ret

class BaseDirFile:
    def __enter__(self):
        self.fobj = open(os.path.join(self.path, self.filename), self.flags)
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
    
    def __iter__(self):
        for path in self.paths:
            yield os.path.join(path, self.filename)
    
    def __str__(self):
        return ':'.join(os.path.join(path, self.filename) for path in self.paths)
    
    def lazy_json(self, existing_only=False, readable_only=False, writeable_only=False):
        import lazyjson
        for path in self.paths:
            if existing_only and not os.path.exists(os.path.join(path, self.filename)):
                continue
            if readable_only:
                try:
                    open(os.path.join(path, self.filename)).close()
                except IOError:
                    continue
            if writeable_only:
                try:
                    open(os.path.join(path, self.filename), 'a').close()
                except IOError:
                    continue
            return lazyjson.File(os.path.join(path, self.filename))
    
    def json(self, base=None):
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
        
        return self.read(patch=_patch_json, base=base)
    
    def read(self, patch=None, base=None):
        """If patch is None (the default), this returns the contents of the first found file.
        
        If patch is not None, it must be a function of the form patch(base, new). This function will then read all existing files in reverse order, and call the patch function with the results of the last call as the first argument, and a file object representing the current file as the second argument. The end result is returned.
        """
        if patch is None:
            for path in self.paths:
                if os.path.exists(os.path.join(path, self.filename)):
                    with open(os.path.join(path, self.filename)) as f:
                        return f.read()
        else:
            for path in reversed(self.paths):
                if os.path.exists(os.path.join(path, self.filename)):
                    with open(os.path.join(path, self.filename)) as new:
                        base = patch(base, new)
            return base

class BaseDir:
    def __call__(self, filename, flags='r'):
        return BaseDirFile([self.path], filename, flags=flags)
    
    def __init__(self, envar, default):
        dir = os.environ.get(envar)
        self.path = default if dir is None or dir == '' else dir
    
    def __str__(self):
        return self.path
    
    def config(self, filename):
        return Config(self(filename))

class BaseDirs:
    def __call__(self, filename, flags='r'):
        return BaseDirFile(self.paths, filename, flags=flags)
    
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
    
    def config(self, filename):
        return Config(self(filename))

data_home = BaseDir('XDG_DATA_HOME', os.path.join(os.environ['HOME'], '.local/share'))
config_home = BaseDir('XDG_CONFIG_HOME', os.path.join(os.environ['HOME'], '.config'))
data_dirs = BaseDirs('XDG_DATA_DIRS', ['/usr/local/share', '/usr/share'], data_home)
config_dirs = BaseDirs('XDG_CONFIG_DIRS', ['/etc/xdg'], config_home)
