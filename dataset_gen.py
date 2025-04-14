import pandas as pd
import numpy as np
import random

# Set seed for reproducibility
np.random.seed(42)

# Define number of rows
num_rows = 100

# Generate random data
data = {
    "float": np.random.uniform(1.0, 130.0, num_rows),  # Random floats
    "boolean": np.random.choice([True, False], num_rows),  # Random booleans
    "string": [random.choice(["apple", "banana", "cherry", "date", "elderberry"]) for _ in range(num_rows)],  # Random strings
    "Age": np.random.randint(1, 125, num_rows),  # Random integers
    "Salary": np.random.uniform(200.0, 500.0, num_rows)  # Another float column
}

df = pd.DataFrame(data)

# Introduce missing values (5-10% of data)
num_missing = int(0.075 * num_rows * len(df.columns))  # ~7.5% missing
for _ in range(num_missing):
    i, j = np.random.randint(0, num_rows), np.random.randint(0, len(df.columns))
    df.iat[i, j] = np.nan  # Set random cell to NaN

# Introduce some duplicate rows
num_duplicates = 5
duplicate_rows = df.sample(num_duplicates, random_state=42)
df = pd.concat([df, duplicate_rows], ignore_index=True)

# Introduce datatype errors
error_indices = np.random.choice(df.index, size=5, replace=False)
df.loc[error_indices, "Salary"] = ["error", "wrong", "NaN", "99.5", "invalid"]  # Strings in int column

# Shuffle rows
df = df.sample(frac=1, random_state=42).reset_index(drop=True)

# Save to CSV
df.to_excel("synthetic_dirty_data2.xlsx", index=False)

print("Dataset generated and saved as 'synthetic_dirty_data.csv'")
print(df.head(10))  # Preview first 10 rows
