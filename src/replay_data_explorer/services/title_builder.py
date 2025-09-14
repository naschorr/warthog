from typing import OrderedDict, Optional

import pandas as pd


class TitleBuilder:
    @staticmethod
    def build_title(base_title: str, *, filters: OrderedDict[str, Optional[str]]) -> str:
        """
        Build a dynamic title based on the base title and applied filters.

        Args:
            base_title (str): The main title.
            filters (OrderedDict[str, str]): An ordered dictionary of filter names and their values.
        Returns:
            str: The constructed title with filters appended.
        """
        if not filters:
            return base_title

        filter_parts = [f"{name}: {value}" for name, value in filters.items() if value]
        if not filter_parts:
            return base_title

        filters_str = ", ".join(filter_parts)
        return f"{base_title} ({filters_str})"
