import inspect
import hashlib
import shelve # TODO: Use a better implementation for DB
import __builtin__
import pkg_resources
import sys

def register(function):
    source = inspect.getsource(function)
    print hashlib.sha1(source).hexdigest()
    module = inspect.getmodule(function)
    setattr(module, function.__name__, memoize(function))
    
def deep_hash(function):
    pass 
    # TODO: code here a recursive analysis of the function bytecode
    # two options:
    # - AST
    # - use of co_names (method calls) and co_varnames
         

def get_version(module):
    # Check built-in module
    if module.__name__ == '__builtins__':
        return sys.version 

    # Check explicitly declared module version
    try:
        return getattr(module, 'version', '__version__', 'VERSION', '__VERSION__')
    except AttributeError:
        pass
    
    # Check package declared module version
    try: 
        return pkg_resources.get_distribution(module.__name__).version 
    except: 
        pass
    
    # If no other option work, return the hash of the source-code of the module
    with open(inspect.getfile(module), 'rb') as f:
        return hashlib.sha1(f.read()).hexdigest()

def memoize(function):
    def wrapper(*args):
        if repr(args) not in cache:
            cache[repr(args)] = function(*args) # TODO: Check what is *kargs
        return cache[repr(args)]
    return wrapper

# TODO: Read as binary for caching
def new_open(old_open):
    def wrapper(*args):
        file_cursor = old_open(*args)
        if len(args) == 1 or 'r' in args[1]:
            content = file_cursor.read()
            file_hash = hashlib.sha1(content).hexdigest()
            cache[file_hash] = content
            file_cursor.seek(0)
        return file_cursor
    return wrapper
        
cache = shelve.open('cache')
__builtin__.open = new_open(__builtin__.open)
