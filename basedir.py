import json
import os
import os.path

def parse_version_string():
    path = os.path.abspath(__file__)
    while os.path.islink(path):
        path = os.path.join(os.path.dirname(path), os.readlink(path))
    path = os.path.dirname(path) # go up one level, from repo/basedir.py to repo, where README.md is located
    while os.path.islink(path):
        path = os.path.join(os.path.dirname(path), os.readlink(path))
    try:
        version = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=path).decode('utf-8').strip('\n')
        if version == 'master':
            try:
                with open(os.path.join(path, 'README.md')) as readme:
                    for line in readme.read().splitlines():
                        if line.startswith('This is `python-xdg-basedir` version'):
                            return line.split(' ')[4]
            except:
                pass
        return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=path).decode('utf-8').strip('\n')
    except:
        pass

__version__ = parse_version_string()

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
    
    def lazy_json(self, existing_only=False, readable_only=False, writeable_only=False, default=None):
        """Return a lazyjson object representing the file(s). Requires the lazyjson module.
        
        Optional arguments:
        existing_only -- If true, exclude files from the multifile which don't exist at the time of the call. Defaults to False.
        readable_only -- If true, exclude files from the multifile for which opening in read mode fails at the time of the call. Defaults to False.
        writeable_only -- If true, exclude files from the multifile for which opening in write mode fails at the time of the call. Defaults to False.
        default -- A JSON-encodable Python object which is appended to the end of the multifile as a lazyjson.PythonFile, and can be used to provide default values for config files. Defaults to None.
        
        Returns:
        A lazyjson.MultiFile created from the paths of this file.
        
        Raises:
        ImportError for lazyjson.
        """
        import lazyjson
        
        paths = []
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
            paths.append(os.path.join(path, self.filename))
        paths.append(lazyjson.PythonFile(default))
        return lazyjson.MultiFile(*paths)
    
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
        self.path = os.environ.get(envar) or default
    
    def __str__(self):
        return self.path
    
    def config(self, filename):
        return Config(self(filename))

class BaseDirs:
    def __call__(self, filename, flags='r'):
        return BaseDirFile([self.home] + self.paths, filename, flags=flags)
    
    def __init__(self, envar, default, home):
        self.home = home
        self.paths = os.environ.get(envar).split(':') or default
    
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
cache_home = BaseDir('XDG_CACHE_HOME', os.path.join(os.environ['HOME'], '.cache'))
