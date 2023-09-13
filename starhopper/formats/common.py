import dataclasses


@dataclasses.dataclass
class Location:
    """
    Stores the location of a piece of data in a file.
    """

    start: int
    end: int

    @property
    def size(self):
        return self.end - self.start
