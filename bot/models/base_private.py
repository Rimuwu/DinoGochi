import sys
import os
from typing import Any

class PrivateModelMixin:
    def __setattr__(self, name: str, value: Any) -> None:
        # Allow internal/private attributes starting with '_' and key Beanie attributes
        if name.startswith('_') or name in ('id', 'revision_id'):
            super().__setattr__(name, value)
            return

        # Check caller frame
        try:
            frame = sys._getframe(1)
            caller_filename = frame.f_code.co_filename
        except ValueError:
            super().__setattr__(name, value)
            return

        # Get the module path of the class where this mixin is mixed in
        cls_module = sys.modules.get(self.__class__.__module__)
        if cls_module and hasattr(cls_module, '__file__') and cls_module.__file__:
            model_file = os.path.abspath(cls_module.__file__)
            # Allow modification from the class's own module file
            if os.path.abspath(caller_filename) == model_file:
                super().__setattr__(name, value)
                return

        # Allow internal framework operations (pydantic, beanie, motor, pymongo, bson)
        caller_lower = caller_filename.lower()
        if any(lib in caller_lower for lib in ('pydantic', 'beanie', 'bson', 'motor', 'pymongo', 'contextlib', 'unittest', 'mock')):
            super().__setattr__(name, value)
            return

        # Deny direct assignment
        raise AttributeError(
            f"Direct modification of field '{name}' on {self.__class__.__name__} is prohibited from outside the model class. "
            f"Please use class/instance methods to mutate data."
        )
