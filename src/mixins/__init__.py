"""
Mixin classes for War Thunder data models.

This module exports mixins that can be used to add common functionality to classes.
"""

from .from_json import FromJsonMixin
from .abstract.to_json import ToJsonMixin

__all__ = ["FromJsonMixin", "ToJsonMixin"]
