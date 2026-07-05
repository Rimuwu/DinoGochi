from pydantic import BaseModel, Field, model_validator, ConfigDict
from typing import List, Any

class DictModel(BaseModel):
    model_config = ConfigDict(extra='allow', populate_by_name=True)

    def __getitem__(self, item):
        if item == 'class':
            item = 'class_name'
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item)

    def get(self, item, default=None):
        if item == 'class':
            item = 'class_name'
        return getattr(self, item, default)

    def __contains__(self, item):
        if item == 'class':
            item = 'class_name'
        return hasattr(self, item)

    def keys(self):
        keys_set = set(self.model_fields.keys()).union(self.__pydantic_extra__ or {})
        if 'class_name' in keys_set:
            keys_set.remove('class_name')
            keys_set.add('class')
        return keys_set

    def values(self):
        return [self.get(k) for k in self.keys()]

    def items(self):
        return [(k, self.get(k)) for k in self.keys()]

class NSmaterial(DictModel):
    item_id: str = ""
    count: int = 1

    @model_validator(mode='before')
    @classmethod
    def validate_before(cls, value: Any):
        if isinstance(value, str):
            return {"item_id": value, "count": 1}
        return value

class NSelement(DictModel):
    create: List[NSmaterial] = Field(default_factory=list)
    materials: List[NSmaterial] = Field(default_factory=list)