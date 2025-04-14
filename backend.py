from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np
import io
import json
from typing import Dict, List, Any
from collections import defaultdict
import math
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Data Quality API",
              description="API for running data quality checks on CSV files")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom JSON encoder to handle NaN, inf, -inf
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, float):
            if math.isnan(obj):
                return "NaN"
            elif math.isinf(obj):
                if obj > 0:
                    return "Infinity"
                else:
                    return "-Infinity"
        return super().default(obj)

def clean_for_json(obj):
    """Recursively clean an object for JSON serialization, replacing NaN, inf, -inf with strings."""
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_for_json(item) for item in obj]
    elif isinstance(obj, float):
        if math.isnan(obj):
            return "NaN"
        elif math.isinf(obj):
            return "Infinity" if obj > 0 else "-Infinity"
        return obj
    elif isinstance(obj, (int, str, bool, type(None))):
        return obj
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        if np.isnan(obj):
            return "NaN"
        elif np.isinf(obj):
            return "Infinity" if obj > 0 else "-Infinity"
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return clean_for_json(obj.tolist())
    else:
        return str(obj)  # Convert other types to string

def detect_missing_values(df):
    """Find missing values in each column."""
    missing_report = df.isnull().sum().reset_index()
    missing_report.columns = ["Column", "Missing_Count"]
    missing_report["Missing_Percentage"] = (missing_report["Missing_Count"] / len(df)) * 100
    
    # Convert to dictionary format for JSON serialization
    if missing_report[missing_report["Missing_Count"] > 0].empty:
        return "None"
    
    result = []
    for _, row in missing_report[missing_report["Missing_Count"] > 0].iterrows():
        result.append({
            "Column": row["Column"],
            "Missing_Count": int(row["Missing_Count"]),
            "Missing_Percentage": float(row["Missing_Percentage"])
        })
    return result

def detect_data_type_mismatches(df):
    """
    Detects mismatched data types in DataFrame columns.
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
                    mixed_indices[val_type.__name__].append(int(idx))
            
            # Format type counts for readability
            type_counts_dict = {t.__name__: int(count) for t, count in type_counts.items()}
            
            mismatches[col] = {
                "dominant_type": dominant_type.__name__,
                "type_counts": type_counts_dict,
                "mixed_indices": dict(mixed_indices)
            }
            
    return mismatches

def format_data_type_mismatches(mismatches):
    """
    Formats data type mismatches into a list of strings.
    """
    if not mismatches:
        return "None"
    
    result = []
    
    for column, info in mismatches.items():
        dominant = info['dominant_type']
        types_str = ", ".join([f"{t} ({count})" for t, count in info['type_counts'].items()])
        result.append(f"{column}: Mixed types [{types_str}]")
    
    return result

def detect_duplicates(df):
    """Find duplicate rows in the dataset."""
    duplicate_count = int(df.duplicated().sum())
    duplicate_indices = df.duplicated().to_numpy().nonzero()[0].tolist()
    return {
        "count": duplicate_count,
        "indices": [int(idx) for idx in duplicate_indices] if duplicate_count > 0 else []
    }

def detect_invalid_inputs(df, rules):
    """Check for invalid inputs based on predefined rules."""
    invalid_entries = {}
    for col, rule in rules.items():
        if col in df.columns:
            invalid_mask = ~df[col].astype(str).str.match(rule, na=False)
            if invalid_mask.any():
                invalid_indices = invalid_mask.to_numpy().nonzero()[0].tolist()
                
                # Convert values to a safe format for JSON
                values = []
                for val in df.loc[invalid_mask, col].tolist():
                    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                        values.append(str(val))
                    else:
                        values.append(val)
                
                invalid_entries[col] = {
                    "count": int(invalid_mask.sum()),
                    "indices": [int(idx) for idx in invalid_indices],
                    "values": values
                }
    return invalid_entries if invalid_entries else "None"

def check_consistency(df, consistency_rules):
    """Check consistency constraints across columns, handling non-numeric values safely."""
    inconsistencies = {}

    for rule_name, rule_func in consistency_rules.items():
        try:
            failed_mask = ~df.apply(lambda row: rule_func(row), axis=1)
            
            if failed_mask.any():
                failed_indices = failed_mask.to_numpy().nonzero()[0].tolist()
                
                # Get rows data in a safe format for JSON
                failed_rows = []
                for _, row in df.loc[failed_mask].iterrows():
                    clean_row = {}
                    for key, val in row.items():
                        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                            clean_row[key] = str(val)
                        else:
                            clean_row[key] = val
                    failed_rows.append(clean_row)
                
                inconsistencies[rule_name] = {
                    "count": int(failed_mask.sum()),
                    "indices": [int(idx) for idx in failed_indices],
                    "rows": failed_rows
                }
        except Exception as e:
            inconsistencies[rule_name] = {
                "error": str(e),
                "message": f"Error checking rule: {rule_name}"
            }

    return inconsistencies if inconsistencies else "None"

def run_data_quality_checks(df):
    """Run all data quality checks and return results as a JSON-serializable dict."""
    results = {}
    
    # 1. Missing Values
    results["missing_values"] = detect_missing_values(df)
    
    # 2. Data Type Mismatches
    data_type_issues = detect_data_type_mismatches(df)
    results["data_type_mismatches"] = {
        "detailed": data_type_issues,
        "summary": format_data_type_mismatches(data_type_issues)
    }
    
    # 3. Duplicates
    results["duplicates"] = detect_duplicates(df)
    
    # 4. Invalid Inputs (define regex-based validation)
    validation_rules = {
        # Add default validation rules here if needed
    }
    results["invalid_inputs"] = detect_invalid_inputs(df, validation_rules)
    
    # 5. Consistency Checks
    consistency_rules = {
        "Valid Age": lambda row: 0 <= pd.to_numeric(row["Age"], errors="coerce") <= 120 if "Age" in row.index else True,
        "Salary Non-negative": lambda row: pd.to_numeric(row["Salary"], errors="coerce") >= 0 if "Salary" in row.index else True,
        "String in set": lambda row: row["string"] in ["apple", "banana", "cherry", "date", "elderberry"] if "string" in row else True
    }
    results["consistency_issues"] = check_consistency(df, consistency_rules)
    
    # Clean any problematic values for JSON serialization
    return clean_for_json(results)

@app.post("/analyze", response_class=JSONResponse)
async def analyze_csv(file: UploadFile = File(...)):
    """
    Upload a CSV file for data quality analysis.
    """
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="File must be a Excel")
    
    try:
        # Read the CSV file into a pandas DataFrame
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        print(df["Salary"])
        print(df.loc[df["boolean"].apply(lambda x: isinstance(x, (bool))), "boolean"])



        # Run all data quality checks
        results = run_data_quality_checks(df)
        # Add basic file info to the results
        results["file_info"] = {
            "filename": file.filename,
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": df.columns.tolist()
        }
        
        # Ensure the response is JSON serializable
        results= clean_for_json(results)
        return {'success': True, "data": results}
    
    except Exception as e:
        return {'success': False, "error": str(e)}
        # raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.post("/analyze/custom", response_class=JSONResponse)
async def analyze_csv_custom(
    file: UploadFile = File(...),
    validation_rules: Dict[str, str] = None,
    consistency_rules: Dict[str, Dict[str, Any]] = None
):
    """
    Upload a CSV file for data quality analysis with custom validation and consistency rules.
    
    - validation_rules: Dictionary mapping column names to regex patterns
    - consistency_rules: Dictionary of custom consistency rules
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        # Read the CSV file into a pandas DataFrame
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        results = {}
        
        # 1. Missing Values
        results["missing_values"] = detect_missing_values(df)
        
        # 2. Data Type Mismatches
        data_type_issues = detect_data_type_mismatches(df)
        results["data_type_mismatches"] = {
            "detailed": data_type_issues,
            "summary": format_data_type_mismatches(data_type_issues)
        }
        
        # 3. Duplicates
        results["duplicates"] = detect_duplicates(df)
        
        # 4. Custom validation rules if provided
        if validation_rules:
            results["invalid_inputs"] = detect_invalid_inputs(df, validation_rules)
        else:
            results["invalid_inputs"] = "None"
        
        # 5. Custom consistency rules if provided
        if consistency_rules:
            # Convert string rules to lambda functions (this is a simplified approach)
            # In a real-world scenario, you'd want more security around this
            parsed_rules = {}
            for rule_name, rule_spec in consistency_rules.items():
                # This is a very simplified approach - in production you would need a more secure way
                # to handle custom rules rather than eval
                column = rule_spec.get("column", "")
                operator = rule_spec.get("operator", "==")
                value = rule_spec.get("value", "")
                
                if column and column in df.columns:
                    # Create a simple lambda based on the specification
                    if operator in ["==", "!=", "<", ">", "<=", ">="]:
                        parsed_rules[rule_name] = lambda row, col=column, op=operator, val=value: \
                            eval(f"pd.to_numeric(row['{col}'], errors='coerce') {op} {val}") \
                            if col in row.index else True
            
            results["consistency_issues"] = check_consistency(df, parsed_rules)
        else:
            # Default consistency rules
            default_rules = {
                "Valid Age": lambda row: 0 <= pd.to_numeric(row["Age"], errors="coerce") <= 120 if "Age" in row.index else True,
                "Salary Non-negative": lambda row: pd.to_numeric(row["Salary"], errors="coerce") >= 0 if "Salary" in row.index else True
            }
            results["consistency_issues"] = check_consistency(df, default_rules)
        
        # Add basic file info to the results
        results["file_info"] = {
            "filename": file.filename,
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": df.columns.tolist()
        }
        
        # Ensure the response is JSON serializable
        return clean_for_json(results)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint for the Data Quality API."""
    return {
        "message": "Welcome to the Data Quality API",
        "endpoints": {
            "/analyze": "Upload a CSV file for data quality analysis",
            "/analyze/custom": "Upload a CSV with custom validation and consistency rules"
        },
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)