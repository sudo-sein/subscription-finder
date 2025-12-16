from utils import clean_amount, translate_column_names, unify_column_names, standard_columns, normalize_description
import sys
import pandas as pd
import numpy as np
import argparse
import difflib

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Analyze CSV for subscription candidates.')
parser.add_argument('file_path', help='Path to the CSV file to analyze.')
parser.add_argument('--threshold', '-t', type=float, default=0.15,
                    help='Percentage threshold for clustering similar amounts (e.g., 0.15 for 15%%). Default is 0.15.')
parser.add_argument('--recency-days', '-r', type=int, default=90,
                    help='Number of days from the latest transaction to consider a subscription active. Default is 90 days.')
parser.add_argument('--debug', '-d', action='store_true',
                    help='Enable debug mode to show verbose output.')
args = parser.parse_args()

file_path = args.file_path

def find_data_start(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        for i, line in enumerate(file):
            line_lower = line.lower()
            if (any(kw in line_lower for kw in standard_columns['Date']) and
                any(kw in line_lower for kw in standard_columns['Description']) and
                any(kw in line_lower for kw in standard_columns['Amount'])):
                return i
    return None

def merge_similar_descriptions(df, threshold=0.7):
    """
    Groups similar descriptions using fuzzy matching and prefix checking.
    Prioritizes shorter names as representatives (e.g., "TRUIST" over "TRUIST LN...").
    """
    if df.empty:
        return df

    unique_descs = df['Description'].dropna().unique()
    # Sort by length (shortest first) to prefer simpler names as representatives
    sorted_descs = sorted(unique_descs, key=len)
    
    mapping = {}
    reps = []
    
    for desc in sorted_descs:
        match = None
        for rep in reps:
            # Check 1: Prefix match (strong signal)
            # e.g., "TRUIST" matches "TRUIST LN..."
            if desc.startswith(rep + " "):
                match = rep
                break
            
            # Check 2: Fuzzy match
            ratio = difflib.SequenceMatcher(None, rep, desc).ratio()
            if ratio > threshold:
                match = rep
                break
        
        if match:
            mapping[desc] = match
        else:
            reps.append(desc)
            mapping[desc] = desc
            
    df['Description'] = df['Description'].map(mapping)
    return df

def get_subscription_candidates(df, groupby=['Description']):
    subscription_candidates = df.groupby(groupby).agg({
        'Amount': ['count', 'sum', 'mean'],
        'Date': ['min', 'max']
    }).reset_index()
    # Flatten columns: Description, count, sum, mean, min, max
    subscription_candidates.columns = ['Description', 'Transaction_Count', 'Total_Spent', 'Amount', 'First_Transaction', 'Last_Transaction']
    subscription_candidates = subscription_candidates[subscription_candidates['Transaction_Count'] > 1]
    return subscription_candidates


start_row = find_data_start(file_path)
if args.debug:
    print(f"Offseting by {start_row} rows.")

if start_row is not None:
    df = pd.read_csv(file_path, skiprows=start_row, sep=',', index_col=False,)
else:
    print("No valid data header found in the file.")
    print(start_row)
    print("Exiting.")
    exit(1)
    
# Example: Translate column names
if not df.empty:
    
    # Check if 'Outflow' exists before translation/unification
    is_outflow_present = any(col.lower() == 'outflow' for col in df.columns)

    df.columns = translate_column_names(df.columns, src_lang='auto')
    df = unify_column_names(df, standard_columns)

    # Example: Convert 'Date' column to datetime
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    df['Amount'] = pd.to_numeric(df['Amount'].apply(clean_amount), errors='coerce')

    if is_outflow_present:
        # Outflow is usually positive, but we want negative for expenses
        # Only invert positive values (income/refunds in Outflow column would be negative in YNAB but let's assume simple case)
        # Actually YNAB: Outflow is positive number. Inflow is positive number.
        # If we mapped Outflow to Amount, we have positive numbers.
        # We need negative numbers for the filter logic below.
        df['Amount'] = df['Amount'].apply(lambda x: -abs(x) if x > 0 else x)

    # Example: Handle missing values
    df.dropna(subset=['Description', 'Amount'], inplace=True)
    
    # Normalize descriptions
    df['Description'] = df['Description'].apply(normalize_description)

    # Merge similar descriptions (fuzzy matching)
    df = merge_similar_descriptions(df)

    subscription_candidates = get_subscription_candidates(df, groupby=['Description'])
    subscription_candidates['First_Transaction'] = pd.to_datetime(subscription_candidates['First_Transaction'])
    subscription_candidates['Last_Transaction'] = pd.to_datetime(subscription_candidates['Last_Transaction'])
    subscription_candidates['Total_Days'] = (subscription_candidates['Last_Transaction'] - subscription_candidates['First_Transaction']).dt.days
    subscription_candidates['Avg_Days_Between_Transactions'] = subscription_candidates['Total_Days'] / (subscription_candidates['Transaction_Count'] - 1)
    
    subscription_candidates = subscription_candidates[(subscription_candidates['Avg_Days_Between_Transactions'] > 25) & (subscription_candidates['Avg_Days_Between_Transactions'] < 35)]
    
    subscription_candidates = subscription_candidates[(subscription_candidates['Amount'] < -10) & (subscription_candidates['Amount'] > -1000)]
    
    # Calculate yearly cost
    subscription_candidates['Yearly_Cost'] = subscription_candidates['Amount'] * 12

    # Filter by recency
    if not df['Date'].empty:
        max_date = df['Date'].max()
        cutoff_date = max_date - pd.Timedelta(days=args.recency_days)
        print(f"Filtering for subscriptions active since {cutoff_date.date()} (last {args.recency_days} days of data).")
        subscription_candidates = subscription_candidates[subscription_candidates['Last_Transaction'] >= cutoff_date]

    print("Number of potential subscriptions:", len(subscription_candidates))
    
    # Display potential subscriptions
    output_df = subscription_candidates[['Description', 'Amount', 'Yearly_Cost', 'Last_Transaction', 'Transaction_Count']].copy()
    output_df = output_df.sort_values('Yearly_Cost', ascending=True)
    print(output_df.to_string(float_format="{:.2f}".format))
else:
    print("Dataframe is empty.")
# print(df.head())