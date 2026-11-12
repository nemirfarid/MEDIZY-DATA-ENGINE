import pandas as pd

df = pd.read_csv('C:/Users/pc lenovo/Downloads/Google Maps Extractor/all-task-1-overview.csv', low_memory=False, nrows=5)
print("Columns in all-task-1-overview.csv:", df.columns.tolist())

