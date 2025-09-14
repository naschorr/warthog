import pandas as pd


class DataFilterer:
    """
    Service for filtering and cleaning replay data.
    """

    def filter_outliers(self, df: pd.DataFrame, column: str, std_dev: float) -> pd.DataFrame:
        """
        Remove outliers from the DataFrame based on standard deviation from the mean.

        Args:
            df: Input DataFrame
            column: Name of the column to use for outlier detection
            std_dev: Number of standard deviations from mean to use as threshold (default: 2.0)

        Returns:
            DataFrame with outliers removed
        """
        if df.empty or column not in df.columns:
            print(f"❌ Column '{column}' not found in DataFrame or DataFrame is empty")
            return df

        # Calculate mean and standard deviation
        mean = df[column].mean()
        std = df[column].std()

        # Calculate bounds
        lower_bound = mean - (std_dev * std)
        upper_bound = mean + (std_dev * std)

        # Filter data
        filtered_df = df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]

        return pd.DataFrame(filtered_df)

    def filter_data(self, df: pd.DataFrame, column: str, allowed_values: list = []) -> pd.DataFrame:
        """
        Filter the DataFrame based on allowed values in a specified column.

        Args:
            df: Input DataFrame
            column: Name of the column to filter on
            allowed_values: List of allowed values for filtering (default: empty list)

        Returns:
            Filtered DataFrame
        """
        if df.empty or column not in df.columns:
            print(f"❌ Column '{column}' not found in DataFrame or DataFrame is empty")
            return df

        if not allowed_values:
            return df

        filtered_df = df[df[column].isin(allowed_values)]

        return pd.DataFrame(filtered_df)
