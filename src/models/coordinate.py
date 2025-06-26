class Coordinate:

    ## Lifecycle

    def __init__(self, x: int, y: int):
        self._x = x
        self._y = y

    ## Megic Methods

    def __repr__(self):
        return f"Coordinate({self.x}, {self.y})"

    def __eq__(self, other):
        if not isinstance(other, Coordinate):
            raise TypeError("Comparison must be with another Coordinate")

        return self.x == other.x and self.y == other.y

    def __gt__(self, other):
        if not isinstance(other, Coordinate):
            raise TypeError("Comparison must be with another Coordinate")

        return self.x >= other.x and self.y >= other.y

    def __lt__(self, other):
        if not isinstance(other, Coordinate):
            raise TypeError("Comparison must be with another Coordinate")

        return self.x <= other.x and self.y <= other.y

    ## Properties

    @property
    def x(self) -> int:
        """X coordinate."""
        return self._x

    @property
    def y(self) -> int:
        """Y coordinate."""
        return self._y

    ## Methods

    def to_tuple(self) -> tuple[int, int]:
        """Convert to a tuple representation."""
        return (self.x, self.y)
