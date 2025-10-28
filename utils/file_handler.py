"""
File handling utilities for CSV data management.

This module provides functions for reading CSV files with proper error handling
and configuration management.
"""

import os

import pandas as pd

from utils.config import FILE_PATHS


def get_file_path(file_key: str) -> str:
    """
    Get file path for specified CSV data file.

    Args:
        file_key (str): Key for the required file path

    Returns:
        str: Full file path for the CSV file

    Raises:
        KeyError: If file_key is not found in FILE_PATHS
    """
    if file_key not in FILE_PATHS:
        raise KeyError(f"File path key '{file_key}' not found in configuration")
    return FILE_PATHS[file_key]


def read_csv_file(file_key):
    """
    Read CSV file using configured file paths.

    Args:
        file_key (str): Key for the CSV file in FILE_PATHS configuration
        **kwargs: Additional arguments to pass to pandas.read_csv()

    Returns:
        Optional[pd.DataFrame]: DataFrame containing CSV data, None if error occurs
    """
    try:
        file_path = get_file_path(file_key)
        if not os.path.exists(file_path):
            print(f"WARNING: CSV file not found at path: {file_path}")
            return None

        df = pd.read_csv(file_path)
        print(f"Successfully loaded CSV file: {file_path} ({len(df)} rows)")
        return df
    except FileNotFoundError:
        print(f"ERROR: CSV file not found for key '{file_key}'")
        return None
    except pd.errors.EmptyDataError:
        print(f"ERROR: CSV file is empty for key '{file_key}'")
        return None
    except (pd.errors.ParserError, ValueError, KeyError) as e:
        print(f"ERROR: Failed to read CSV file for key '{file_key}'. Reason: {e}")
        return None
