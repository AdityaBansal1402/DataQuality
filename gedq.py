import pandas as pd
from great_expectations.validator.validator import Validator
from great_expectations.core.expectation_suite import ExpectationSuite
from great_expectations.datasource.fluent.execution_engine import PandasExecutionEngine
from great_expectations.datasource.fluent.batch_request import BatchData

def get_validator_for_dataframe(df):
    engine = PandasExecutionEngine()
    suite = ExpectationSuite(name="my_suite")

    batch_data = BatchData(data=df)
    batch = engine.get_batch_data_and_markers(batch_data)

    validator = Validator(
        execution_engine=engine,
        batches=[batch[0]],  # batch_data, batch_markers
        expectation_suite=suite
    )

    return validator



# ----------------------------
# ✅ Rule Dictionary
# ----------------------------
rule_dict = {
    1: "expect_column_mean_to_be_between",
    2: "expect_column_median_to_be_between",
    3: "expect_column_values_to_be_between",
    4: "expect_column_max_to_be_between",
    5: "expect_column_min_to_be_between",
    6: "expect_column_values_to_not_be_null",
    7: "expect_column_values_to_be_unique",
    8: "expect_column_value_lengths_to_be_between",
    9: "expect_column_values_to_be_in_set",
    10: "expect_column_values_to_match_regex",
    11: "expect_column_values_to_match_strftime_format",
    12: "expect_column_values_to_be_of_type",
    13: "expect_column_values_to_be_null",
}

# ----------------------------
# ✅ Apply Rule
# ----------------------------
def apply_rule(validator: Validator, column_name: str, rule_number: int, **kwargs):
    method_name = rule_dict.get(rule_number)
    if not method_name:
        raise ValueError(f"Invalid rule number: {rule_number}")
    
    method = getattr(validator, method_name, None)
    if not method:
        raise ValueError(f"Validator does not support method '{method_name}'")
    
    print(f"Applying {method_name} on '{column_name}' with args {kwargs}")
    return method(column=column_name, **kwargs)

# ----------------------------
# ✅ Example Usage
# ----------------------------
if __name__ == "__main__":
    df = pd.DataFrame({
        "revenue": [100, 200, 300, 400, 500],
        "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
        "active": [True, False, True, True, False]
    })

    validator = get_validator_for_dataframe(df)

    apply_rule(validator, "revenue", 1, min_value=50, max_value=600)
    apply_rule(validator, "name", 8, min_value=3, max_value=10)
    apply_rule(validator, "active", 9, value_set=[True, False])

    print("\n--- Expectations Applied ---")
    for exp in validator.get_expectation_suite().expectations:
        print(exp)
