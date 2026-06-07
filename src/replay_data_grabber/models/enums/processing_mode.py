from enum import Enum


class ProcessingMode(str, Enum):
    FILE = "file"
    ALL = "all"
    NEW = "new"
