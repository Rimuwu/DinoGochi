import importlib

def func_to_str(func):
    """Преобразует функцию в строку вида 'модуль.имя_функции'."""
    return f"{func.__module__}.{func.__name__}"

def str_to_func(func_path):
    """Получает функцию по строке вида 'модуль.имя_функции'."""

    module_name, func_name = func_path.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, func_name)