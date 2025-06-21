import re

from pydantic import BaseModel, Field


class Currency(BaseModel):
    """
    Represents in-game currency values in War Thunder.

    Attributes:
        silver_lions: Silver Lions (SL) amount
        research_points: Research Points (RP) amount (always represents the total)
        convertible_research_points: Convertible Research Points (CRP) amount
    """
    silver_lions: int = Field(default=0, description="Silver Lions (SL)")
    research_points: int = Field(default=0, description="Research Points (RP)")
    convertible_research_points: int = Field(default=0, description="Convertible Research Points (CRP)")

    ## Properties

    @property
    def sl(self) -> int:
        """Shorthand getter for silver_lions."""
        return self.silver_lions

    @property
    def rp(self) -> int:
        """Shorthand getter for research_points."""
        return self.research_points

    @property
    def crp(self) -> int:
        """Shorthand getter for convertible_research_points."""
        return self.convertible_research_points

    ## Magic Methods

    def __str__(self) -> str:
        """String representation of currency values."""
        parts = []
        if self.silver_lions:
            parts.append(f"{self.silver_lions} SL")
        if self.research_points:
            parts.append(f"{self.research_points} RP")
        if self.convertible_research_points:
            parts.append(f"{self.convertible_research_points} CRP")

        return ", ".join(parts) if parts else "0"

    ## Methods

    @classmethod
    def from_strings(cls, *, sl: str = "", rp: str = "", crp: str = "") -> "Currency":
        currency = cls()

        if (sl):
            sl_match = re.search(r"\s*(\d+)\s+SL\s*$", sl)
            if (sl_match):
                currency.silver_lions = int(sl_match.group(1))

        if (rp):
            rp_match = re.search(r"\s*(\d+)\s+RP\s*$", rp)
            if (rp_match):
                currency.research_points = int(rp_match.group(1))

        if (crp):
            crp_match = re.search(r"\s*(\d+)\s+CRP\s*$", crp)
            if (crp_match):
                currency.convertible_research_points = int(crp_match.group(1))

        return currency
