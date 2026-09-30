

def get_func_args(func):
    while hasattr(func, "__wrapped__"):
        func = func.__wrapped__
    code = func.__code__
    size = code.co_argcount + code.co_kwonlyargcount
    return code.co_varnames[:size]