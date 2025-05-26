import pandas as pd
import great_expectations as ge

df = pd.DataFrame({"age": [20, 30, 150, 10, 25, -5]})
ge_df = ge.from_pandas(df)

result = ge_df.expect_column_values_to_be_between(
    column="age",
    min_value=18,
    max_value=65,
    result_format={
        "result_format": "COMPLETE",
        "include_unexpected_index_list": True
    }
)

print(result["result"].keys())  # should include "unexpected_index_list"
print(result["result"].get("unexpected_index_list"))