import collections.abc
import json
import os
import os.path
import pathlib
import subprocess

def parse_version_string():
    path = pathlib.Path(__file__).resolve().parent # go up one level, from repo/basedir.py to repo, where README.md is located
    try:
        version = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=str(path)).decode('utf-8').strip('\n')
        if version == 'master':
            try:
                with (path / 'README.md').open() as readme:
                    for line in readme.read().splitlines():
                        if line.startswith('This is `python-xdg-basedir` version '):
                            return line.split(' ')[4]
            except:
                pass
        return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=str(path)).decode('utf-8').strip('\n')
    except:
        pass

__version__ = parse_version_string()

class BaseDirFile(collections.abc.Sequence):
    def __init__(self, paths, filename, flags='r'):
        self.paths = [pathlib.Path(p) for p in paths]
        self.filename = filename
        self.flags = 'r'

        def __enter__(self):
        self.fobj = (self.path / self.filename).open(self.flags)
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

    def __getitem__(self, value):
        if isinstance(value, slice):
            return [path / self.filename for path in self.paths[value]]
        else:
            return self.paths[value] / self.filename
        
    def __iter__(self):
        for path in self.paths:
            yield path / self.filename

    def __len__(self):
        return len(self.paths)

    def __str__(self):
        return ':'.join(str(path / self.filename) for path in self.paths)

    def lazy_json(self, existing_only=False, readable_only=False, writeable_only=False, default=None, *, init=False):
        """Return a lazyjson object representing the file(s). Requires the lazyjson module.

        Optional arguments:
        existing_only -- If true, exclude files from the multifile which don't exist at the time of the call. Defaults to False.
        readable_only -- If true, exclude files from the multifile for which opening in read mode fails at the time of the call. Defaults to False.
        writeable_only -- If true, exclude files from the multifile for which opening in write mode fails at the time of the call. Defaults to False.
        default -- A JSON-encodable Python object which is appended to the end of the multifile as a lazyjson.PythonFile, and can be used to provide default values for config files. Defaults to None.

        Keyword-only arguments:
        init -- If true, create the file on the first path if none of the files exists, and write the “default” argument to it. Defaults to False.

        Returns:
        A lazyjson.MultiFile created from the paths of this file.

        Raises:
        ImportError for lazyjson.
        """
        import lazyjson

        paths = []
        for path in self.paths:
            if existing_only and not (path / self.filename).exists():
                continue
            if readable_only:
                try:
                    (path / self.filename).open().close()
                except IOError:
                    continue
            if writeable_only:
                try:
                    (path / self.filename).open('a').close()
                except IOError:
                    continue
            paths.append(path / self.filename)
        if init and not any((path / self.filename).exists() for path in self.paths):
            for path in self.paths:
                try:
                    with (path / self.filename).open('w') as f:
                        json.dump(default, f, indent=4, sort_keys=True)
                        print(file=f)
                except IOError:
                    continue
                else:
                    break
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

    @property
    def path(self):
        for iter_path in self.paths:
            if (iter_path / filename).exists():
                return iter_path

    def read(self, patch=None, base=None):
        """If patch is None (the default), this returns the contents of the first found file.

        If patch is not None, it must be a function of the form patch(base, new). This function will then read all existing files in reverse order, and call the patch function with the results of the last call as the first argument, and a file object representing the current file as the second argument. The end result is returned.
        """
        if patch is None:
            for path in self.paths:
                if (path / self.filename).exists():
                    with (path / self.filename).open() as f:
                        return f.read()
        else:
            for path in reversed(self.paths):
                if (path / self.filename).exists():
                    with (path / self.filename).open() as new:
                        base = patch(base, new)
            return base

class BaseDir:
    def __call__(self, filename, flags='r'):
        return BaseDirFile([self.path], filename, flags=flags)

    def __init__(self, envar, default):
        self.path = pathlib.Path(os.environ.get(envar) or default)

    def __str__(self):
        return str(self.path)

    def config(self, filename):
        return Config(self(filename))

class BaseDirs:
    def __call__(self, filename, flags='r'):
        return BaseDirFile([self.home] + self.paths, filename, flags=flags)

    def __init__(self, envar, default, home):
        if isinstance(home, BaseDir):
            self.home = home.path
        else:
            self.home = pathlib.Path(home)
        self.paths = os.environ.get(envar) or default
        if isinstance(self.paths, str):
            self.paths = [pathlib.Path(p) for p in self.paths.split(':')]

    def __iter__(self):
        yield self.home
        for path in self.paths:
            yield path

    def __str__(self, include_home=False):
        paths = ([self.home] if include_home else []) + list(self.paths)
        return ':'.join(str(p) for p in paths)

    def config(self, filename):
        return Config(self(filename))

data_home = BaseDir('XDG_DATA_HOME', pathlib.Path.home() / '.local' / 'share')
config_home = BaseDir('XDG_CONFIG_HOME', pathlib.Path.home() / '.config')
data_dirs = BaseDirs('XDG_DATA_DIRS', ['/usr/local/share', '/usr/share'], data_home)
config_dirs = BaseDirs('XDG_CONFIG_DIRS', ['/etc/xdg'], config_home)
cache_home = BaseDir('XDG_CACHE_HOME', pathlib.Path.home() / '.cache')
