from dataclasses import dataclass, field

@dataclass
class NSmaterial:
    item_id: str = field(default_factory=str)
    count: int = field(default_factory=int)

@dataclass
class NSelement:
    create: list[NSmaterial] = field(default_factory=list)
    materials: list[NSmaterial] = field(default_factory=list)