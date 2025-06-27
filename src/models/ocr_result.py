from models import Coordinate


class OCRResult:

    # Lifecycle

    def __init__(
        self,
        text: str,
        bounding_box: tuple[Coordinate, Coordinate, Coordinate, Coordinate],
        confidence: float,
    ):
        self._text = text
        self._bounding_box = bounding_box
        self._confidence = confidence
        self._rectangle = self._calculate_rectangle()
        self._origin = self._rectangle[0]

    # Magic Methods

    def __repr__(self):
        return f"OCRResult(text={self._text}, bounding_box={self._bounding_box}, confidence={self._confidence})"

    # Properties

    @property
    def text(self) -> str:
        """
        Get the recognized text.
        """
        return self._text

    @property
    def bounding_box(self) -> tuple[Coordinate, Coordinate, Coordinate, Coordinate]:
        """
        Get the bounding box coordinates of the recognized text.
        """
        return self._bounding_box

    @property
    def rectangle(self) -> tuple[Coordinate, Coordinate]:
        """
        Get the top-left and bottom-right coordinates of the bounding box.
        """
        return self._rectangle

    @property
    def origin(self) -> Coordinate:
        """
        Get the top-left coordinate of the bounding box.
        """
        return self._origin

    # Methods

    def _calculate_rectangle(self) -> tuple[Coordinate, Coordinate]:
        """
        Calculate the top-left and bottom-right coordinates of the bounding box.
        """
        x_coords = [point.x for point in self._bounding_box]
        y_coords = [point.y for point in self._bounding_box]
        return (
            Coordinate(min(x_coords), min(y_coords)),
            Coordinate(max(x_coords), max(y_coords)),
        )
