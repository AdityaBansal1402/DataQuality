from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Body
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np
import io, ast, re, json, math
from typing import Dict, List, Any
from collections import defaultdict
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, RootModel
from typing import List, Optional, Union
from gem import GemBot, sys_text
import great_expectations as ge
from great_expectations.core.batch import RuntimeBatchRequest
import ast

class dframe(BaseModel):
    df: pd.DataFrame

    model_config = ConfigDict(arbitrary_types_allowed=True)

# Create a data context
context = ge.get_context()

# Create a datasource
datasource_config = {
    "name": "pandas_datasource",
    "class_name": "Datasource",
    "module_name": "great_expectations.datasource",
    "execution_engine": {
        "module_name": "great_expectations.execution_engine",
        "class_name": "PandasExecutionEngine"
    },
    "data_connectors": {
        "runtime_connector": {
            "class_name": "RuntimeDataConnector",
            "batch_identifiers": ["batch_id"]
        }
    }
}

# Add the datasource to your context
context.add_or_update_datasource(**datasource_config)

# Create an expectation suite
suite_name = "excel_suite"
context.add_or_update_expectation_suite(expectation_suite_name=suite_name)


app = FastAPI(title="Data Quality API",
              description="API for running data quality checks on CSV files")
g1 = GemBot()
g1.system(sys_text)

temp_df = pd.DataFrame({
    "a": [1, 2],
    "b": [1, 2]
})

dfc = dframe(df = temp_df)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Rule(BaseModel):
    rule_type: str
    value: Optional[str] = None

class ColumnValidationRequest(BaseModel):
    column: str
    dataType: str
    rules: List[Rule]

class ColumnRules(BaseModel):
    type: str
    rules: List[Rule]

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
    
ge_expectations = {
    1: "expect_column_to_exist",
    2: "expect_column_values_to_not_be_null",
    3: "expect_column_values_to_be_null",
    4: "expect_column_values_to_be_unique",
    5: "expect_table_row_count_to_be_between",
    6: "expect_table_column_count_to_be_between",
    7: "expect_column_values_to_be_in_set",
    8: "expect_column_values_to_not_be_in_set",
    9: "expect_column_values_to_be_of_type",
    10: "expect_column_values_to_match_regex",
    11: "expect_column_values_to_not_match_regex",
    12: "expect_column_values_to_match_strftime_format",
    13: "expect_column_values_to_be_between",
    14: "expect_column_mean_to_be_between",
    15: "expect_column_median_to_be_between",
    16: "expect_column_min_to_be_between",
    17: "expect_column_max_to_be_between",
    18: "expect_column_quantile_values_to_be_between",
    19: "expect_column_proportion_of_unique_values_to_be_between",
    20: "expect_column_value_lengths_to_be_between",
    21: "expect_column_value_lengths_to_equal",
    22: "expect_column_pair_values_to_be_equal",
    23: "expect_column_pair_values_a_to_be_greater_than_b",
    24: "expect_compound_columns_to_be_unique",
    25: "expect_select_column_values_to_be_unique_within_record",
    26: "expect_multicolumn_sum_to_equal",
    27: "expect_column_distinct_values_to_be_in_set",
    28: "expect_column_kl_divergence_to_be_less_than",
    29: "expect_column_to_exist_in_list",
    30: "expect_column_values_to_be_json_parseable"
}
 
def apply_expectation(validator, expectation_number, column, *values):
    """
    Applies a Great Expectations function by its assigned number.

    Parameters:
        validator (Validator): The GE Validator object.
        expectation_number (int): The ID of the expectation to apply.
        column (str): The name of the column to validate.
        values (list): A list of positional arguments to pass to the expectation.

    Returns:
        dict: The expectation config dictionary.
    """
    func_name = ge_expectations.get(expectation_number)
    if not func_name:
        raise ValueError(f"Invalid expectation number: {expectation_number}")

    func = getattr(validator, func_name, None)
    if not func:
        raise AttributeError(f"Expectation function '{func_name}' not found on validator")

    return func(column, *values)


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
    
def clean_json_string(messy_string):
    # 1. Unescape \n if it's literally a backslash followed by n
    messy_string = messy_string.replace("\\n", "\n")

    # 2. Remove any Markdown-style ```json...``` wrappers
    messy_string = re.sub(r"^```json\s*", "", messy_string)
    messy_string = re.sub(r"\s*```$", "", messy_string)

    # 3. Remove anything **after the last closing brace**
    # This is your actual fix for "Extra data"
    last_brace = messy_string.rfind("}")
    if last_brace != -1:
        messy_string = messy_string[:last_brace + 1]

    return messy_string.strip()

def detect_missing_values(dataset, validator):
    """
    Uses Great Expectations to detect missing values in all columns.
    Returns a list of dicts with column name, missing count, and missing percentage.
    """
    result = []

    for col in dataset.columns:
        ge_result = validator.expect_column_values_to_not_be_null(col)

        if not ge_result["success"]:
            result.append({
                "Column": col,
                "Missing_Count": int(ge_result["result"].get("unexpected_count", 0)),
                "Missing_Percentage": float(round(ge_result["result"].get("unexpected_percent", 0.0), 2))
            })

    return result if result else "None"

def detect_type_mismatches(dataset, validator):
    """
    Detects type mismatches in a dataset using GE's built-in expectations.
    Assumes PandasDataset or GE dataset.

    Returns a dict of columns where mismatches were found.
    """
    mismatches = {}

    for col in dataset.columns:
        # Skip empty/null columns
        if dataset[col].dropna().empty:
            continue
        
        # Guess the dominant type from non-null values
        dominant_type = dataset[col].dropna().map(type).mode()[0].__name__

        # GE expectation
        result = validator.expect_column_values_to_be_of_type(col, dominant_type)

        if not result["success"]:
            mismatches[col] = {
                "expected_type": dominant_type,
                "unexpected_percent": result["result"].get("unexpected_percent", None),
                "unexpected_count": result["result"].get("unexpected_count", None),
                "partial_unexpected_list": result["result"].get("partial_unexpected_list", [])
            }

    return mismatches

def format_type_mismatches(mismatches):
    if not mismatches:
        return "None"

    formatted = []
    for col, info in mismatches.items():
        formatted.append(
            f"{col}: Expected type '{info['expected_type']}', "
            f"Unexpected count: {info['unexpected_count']}, "
            f"Sample bad values: {info['partial_unexpected_list']}"
        )
    return formatted

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

def run_data_quality_checks(df, validator):
    """Run all data quality checks and return results as a JSON-serializable dict."""
    results = {}
    
    # 1. Missing Values
    results["missing_values"] = detect_missing_values(df, validator)
    
    # 2. Data Type Mismatches
    data_type_issues = detect_type_mismatches(df, validator)
    results["data_type_mismatches"] = {
        "detailed": data_type_issues,
        "summary": format_type_mismatches(data_type_issues)
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

def summarize_validation_results(validation_result):
    """
    Summarizes Great Expectations validation results into readable info.
    Only includes relevant metrics and avoids empty noise.
    """
    summary = []

    for result in validation_result.results:
        expectation_type = result["expectation_config"]["expectation_type"]
        column = result["expectation_config"]["kwargs"].get("column", "N/A")
        success = result["success"]
        result_dict = result.get("result", {})

        entry = {
            "Expectation": expectation_type,
            "Column": column,
            "Success": success
        }

        if "unexpected_percent" in result_dict:
            entry["Failed %"] = round(result_dict["unexpected_percent"], 2)
            entry["Passed %"] = round(100 - result_dict["unexpected_percent"], 2)

        if "unexpected_count" in result_dict:
            entry["Total Records"] = result_dict.get("element_count", "N/A")
            entry["Failed Records"] = result_dict["unexpected_count"]
            entry["Passed Records"] = result_dict.get("element_count", 0) - result_dict["unexpected_count"]

        if "partial_unexpected_list" in result_dict and result_dict["partial_unexpected_list"]:
            entry["Sample Failures"] = result_dict["partial_unexpected_list"][:5]

        summary.append(entry)

    return summary

def smart_cast(value):
    """
    Converts a string to its appropriate Python type.
    """
    try:
        # Safely evaluate literals like numbers, booleans, None, lists, dicts
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        # If it can't be parsed, return as-is (string)
        return value


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
        dfc.df = df
        
        # Create a batch request
        batch_request = RuntimeBatchRequest(
            datasource_name="pandas_datasource",
            data_connector_name="runtime_connector",
            data_asset_name="my_excel_data",
            runtime_parameters={"batch_data": df},
            batch_identifiers={"batch_id": "first_batch"}
        )

        # Get a validator using your batch and expectation suite
        validator = context.get_validator(
            batch_request=batch_request,
            expectation_suite_name=suite_name
        )
        
        gen_rule = g1.gen_out(f"For the following dataframe, please return the expectations that may apply along with arguments:{df}")

        cleaned = clean_json_string(gen_rule)
        print(cleaned)
        gen_rule = json.loads(cleaned)
        
        # Run all data quality checks
        results = run_data_quality_checks(df, validator)

        # Save the expectation suite
        validator.save_expectation_suite(discard_failed_expectations=False)

        # Instead of creating a stored checkpoint, let's run validation directly
        validation_result = validator.validate()

        val_res = summarize_validation_results(validation_result)

        # print(val_res)

        # Add basic file info to the results
        results["file_info"] = {
            "filename": file.filename,
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": df.columns.tolist(),
            "gen_rule": gen_rule,
            "validation_results": val_res
        }
        
        # Ensure the response is JSON serializable
        results= clean_for_json(results)
        return {'success': True, "data": results}
    
    except Exception as e:
        return {'success': False, "error": str(e)}
        # raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.post("/validate")
async def validate_column(request: Request):
    """
    Apply validation rules to a specific column in the current dataset. : ColumnValidationRequest
    """
    try:
        data = await request.json()  # Get the actual JSON from the request

        # Create a batch request
        batch_request = RuntimeBatchRequest(
            datasource_name="pandas_datasource",
            data_connector_name="runtime_connector",
            data_asset_name="my_excel_data",
            runtime_parameters={"batch_data": dfc.df},
            batch_identifiers={"batch_id": "first_batch"}
        )

        # Get a validator using your batch and expectation suite
        validator = context.get_validator(
            batch_request=batch_request,
            expectation_suite_name=suite_name
        )
        # [{'column': 'boolean', 'rules': [{'rule_id': 2, 'value': ''}, {'rule_id': 9, 'value': 'boolean'}]}]
        # {'column': 'boolean', 'rules': [{'rule_id': 2, 'value': ''}, {'rule_id': 9, 'value': 'boolean'}]}
        
        for column_name, rules_info in data.items():
            rule_list = rules_info.get("rules", [])
            for i in rule_list:
                rule_id = i.get("rule_id")
                raw_values = i.get("value").split()
                cleaned_values = [smart_cast(v) for v in raw_values]
                apply_expectation(validator, rule_id, column_name, *cleaned_values)

        # print("Collected rule string:\n", s)

        # rule_string = g1.gen_out(f"The following are the rules created by the user, please return in formatted form:{s}")
        # rule_string = "{" + rule_string + "}"

        # print(rule_string)
        # print(rule_d)

        validation_result = validator.validate()

        results = summarize_validation_results(validation_result)

        # results = check_consistency(dfc.df, rule_d)
        # results = apply_validation_rules(df, request.column, request.dataType, request.rules)
        
        return {'success': True, 'data': clean_for_json(results)}
    
    except Exception as e:
        return {'success': False, 'error': str(e)}

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