from enum import Enum


class Country(Enum):
    """Enum representing different countries in War Thunder."""

    CHINA = "China"
    FRANCE = "France"
    GERMANY = "Germany"
    ISRAEL = "Israel"
    ITALY = "Italy"
    JAPAN = "Japan"
    RUSSIA = "Russia"
    SWEDEN = "Sweden"
    UK = "UK"
    USA = "USA"

    @staticmethod
    def get_country_by_name(name: str) -> "Country":
        """Get the Country enum member by its name."""
        name = name.strip().lower()

        # Simple comparison for substring matches
        for country in Country:
            if country.value.lower() in name:
                return country

        # Handle edge cases where the name doesn't exactly match
        if "britain" in name:
            return Country.UK
        if "ussr" in name:
            return Country.RUSSIA

        raise ValueError(f"Country not found for name: {name}")
