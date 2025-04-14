import great_expectations as ge
from great_expectations.data_context import FileDataContext
from great_expectations.core.batch import BatchRequest
from great_expectations.cli.datasource import sanitize_yaml_and_save_datasource
import json


datasource_name = "my_datasource"

example_yaml = f"""
name: {datasource_name}
class_name: Datasource
execution_engine:
  class_name: PandasExecutionEngine
data_connectors:
  default_inferred_data_connector_name:
    class_name: InferredAssetFilesystemDataConnector
    base_directory: ..
    default_regex: 
      group_names:
        - data_asset_name
      pattern: (.*)\.xlsx
  default_runtime_data_connector_name:
    class_name: RuntimeDataConnector
    assets:
      my_runtime_asset_name:
        batch_identifiers:
          - runtime_batch_identifier_name
"""

# Initialize DataContext
context = FileDataContext()

sanitize_yaml_and_save_datasource(context, example_yaml, overwrite_existing=True)
context.list_datasources()

# Create Expectation Suite
suite_name = "my_suite"
context.create_expectation_suite(expectation_suite_name=suite_name, overwrite_existing=True)

# Define BatchRequest
batch_request = BatchRequest(
    datasource_name="my_datasource",
    data_connector_name="default_inferred_data_connector_name",
    data_asset_name="BNA 114",
    batch_spec_passthrough={
        "reader_method": "read_excel",
        "reader_options": {
            "engine": "openpyxl"
        }
    }
)

# Get a Validator for the Batch
validator = context.get_validator(
    batch_request=batch_request,
    expectation_suite_name=suite_name
)

validator.expect_column_value_lengths_to_be_between(
    column="10/01/2024",
    min_value=0,
    max_value=100
)

validator.expect_column_values_to_be_between(
    column="10/01/2024",
    min_value=0,
    max_value=100  # Adjust this as per your data's expected range
)



results = validator.validate()

# Extract relevant info
relevant_info = []
for result in results["results"]:
    info = {
        "expectation_type": result["expectation_config"]["expectation_type"],
        "success": result["success"],
        "element_count": result["result"].get("element_count", None),
        "unexpected_count": result["result"].get("unexpected_count", None),
        "unexpected_percent": result["result"].get("unexpected_percent", None),
        "partial_unexpected_list": result["result"].get("partial_unexpected_list", [])
    }
    relevant_info.append(info)

# Print relevant info
print(json.dumps(relevant_info, indent=2))

validator.save_expectation_suite()
