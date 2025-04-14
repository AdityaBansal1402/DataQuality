import pandas as pd
import numpy as np
# import kagglehub
import os
from collections import defaultdict


def detect_missing_values(df):
    """Find missing values in each column."""
    missing_report = df.isnull().sum().reset_index()
    missing_report.columns = ["Column", "Missing_Count"]
    missing_report["Missing_Percentage"] = (missing_report["Missing_Count"] / len(df)) * 100
    return missing_report[missing_report["Missing_Count"] > 0]

def detect_data_type_mismatches(df):
    """
    Detects mismatched data types in DataFrame columns.
    
    Args:
        df (pandas.DataFrame): The DataFrame to analyze
        
    Returns:
        dict: Dictionary with columns having mixed data types, showing:
            - dominant_type: The most common type in the column
            - type_counts: Dictionary of type frequencies
            - mixed_indices: Dictionary of indices with non-dominant types
    """
    mismatches = {}
    
    for col in df.columns:
            
        # Get value types for non-null values
        non_null_mask = ~df[col].isna()
        if non_null_mask.sum() == 0:
            continue
            
        # Map each value to its type and count occurrences
        type_series = df.loc[non_null_mask, col].map(type)
        type_counts = type_series.value_counts()
        
        # If we have more than one type in the column, it's a mismatch
        if len(type_counts) > 1:
            dominant_type = type_counts.index[0]
            
            # Find indices with non-dominant types
            mixed_indices = defaultdict(list)
            for idx, val_type in type_series.items():
                if val_type != dominant_type:
                    mixed_indices[val_type.__name__].append(idx)
            
            # Format type counts for readability
            type_counts_dict = {t.__name__: count for t, count in type_counts.items()}
            
            mismatches[col] = {
                "dominant_type": dominant_type.__name__,
                "type_counts": type_counts_dict,
                "mixed_indices": dict(mixed_indices)
            }
            
    return mismatches

def format_data_type_mismatches(mismatches):
    """
    Formats data type mismatches into a simple, readable string.
    
    Args:
        mismatches (dict): Output from detect_data_type_mismatches function
        
    Returns:
        str: Formatted string showing basic mismatch information
    """
    if not mismatches:
        return "None"
    
    result = []
    
    for column, info in mismatches.items():
        dominant = info['dominant_type']
        types_str = ", ".join([f"{t} ({count})" for t, count in info['type_counts'].items()])
        result.append(f"  - {column}: Mixed types [{types_str}]")
    
    return "\n".join(result)

def detect_duplicates(df):
    """Find duplicate rows in the dataset."""
    duplicate_count = df.duplicated().sum()
    return duplicate_count

def detect_invalid_inputs(df, rules):
    """Check for invalid inputs based on predefined rules."""
    invalid_entries = {}
    for col, rule in rules.items():
        if col in df.columns:
            invalid_entries[col] = df[~df[col].astype(str).str.match(rule, na=False)]
    return invalid_entries

def check_consistency(df, consistency_rules):
    """Check consistency constraints across columns, handling non-numeric values safely."""
    inconsistencies = {}

    for rule_name, rule_func in consistency_rules.items():
        failed_rows = df[~df.apply(lambda row: rule_func(row), axis=1, result_type="reduce")]

        if not failed_rows.empty:
            inconsistencies[rule_name] = failed_rows

    return inconsistencies

def run_data_quality_checks(df):
    print("\nRunning Data Quality Checks...\n")
    
    # 1. Missing Values
    missing_values = detect_missing_values(df)
    print(f"Missing Values:\n{missing_values if not missing_values.empty else 'None'}\n")
    
    # 2. Data Type Mismatches
    data_type_issues = detect_data_type_mismatches(df)
    print(f"Data Type Mismatches:\n{format_data_type_mismatches(data_type_issues)}\n")
    
    # 3. Duplicates
    duplicate_count = detect_duplicates(df)
    print(f"Duplicate Rows: {duplicate_count}\n")
    
    # 4. Invalid Inputs (define regex-based validation)
    validation_rules = {
        # "Age": r"^\d+$"
    }
    invalid_inputs = detect_invalid_inputs(df, validation_rules)
    print(f"Invalid Inputs:\n{invalid_inputs if invalid_inputs else 'None'}\n")
    
    # 5. Consistency Checks (e.g., Age should be < 120)
    consistency_rules = {
        "Valid Age": lambda row: 0 <= pd.to_numeric(row["Age"], errors="coerce") <= 120 if "Age" in row else True,
        "Salary Non-negative": lambda row: pd.to_numeric(row["Salary"], errors="coerce") >= 0 if "Salary" in row else True,
        "String in set": lambda row: row["string"] in ["apple", "banana", "cherry", "date", "elderberry"] if "string" in row else True
    }
    consistency_issues = check_consistency(df, consistency_rules)
    print(f"Consistency Issues:\n")
    for element,issue in consistency_issues.items():
        print(element,issue)
        print()

    print("Data Quality Checks Completed.")

if __name__ == "__main__":
    df = pd.read_csv("synthetic_dirty_data.csv")
    run_data_quality_checks(df)
