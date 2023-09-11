import dataclasses


@dataclasses.dataclass
class Location:
    start: int
    end: int
    size: int
