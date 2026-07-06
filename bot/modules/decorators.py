def register_method(cls):
    """ Декоратор для регистрации методов"""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            return func(self, *args, **kwargs)

        setattr(cls, func.__name__, wrapper)
        return func
    return decorator