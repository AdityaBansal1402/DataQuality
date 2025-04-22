import pandas as pd
import numpy as np

dataset = pd.read_excel("synthetic_dirty_data.xlsx")
print(dataset["boolean"].head(10)) 
for col in dataset.columns:
        
        # Skip empty/null columns
        if dataset[col].dropna().empty:
            continue
        
        # Guess the dominant type from non-null values
        dominant_type = dataset[col].dropna().map(type).mode()[0].__name__

        print(f"Column '{col}' has dominant type: {dominant_type}")
