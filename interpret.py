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
parser.add_argument('--min-transaction-amount', type=float, default=10.0,
                    help='Minimum absolute transaction amount to consider for a subscription. Default is 10.0.')
parser.add_argument('--max-transaction-amount', type=float, default=10000.0,
                    help='Maximum absolute transaction amount to consider for a subscription. Default is 10000.0 (i.e., $10,000).')
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

def cluster_amounts(group, threshold):
    # group is a DataFrame subset (for one Description)
    # We want to return the group with 'Amount' updated to the cluster mean
    
    if len(group) < 2:
        return group
        
    # Sort by Amount to ensure deterministic processing
    sorted_group = group.sort_values('Amount')
    amounts = sorted_group['Amount'].values
    
    clusters = [] # List of [values]
    if len(amounts) > 0:
        current_cluster = [amounts[0]]
        
        for val in amounts[1:]:
            ref = current_cluster[0]
            # Avoid division by zero
            if ref == 0:
                if val == 0:
                    current_cluster.append(val)
                else:
                    clusters.append(current_cluster)
                    current_cluster = [val]
                continue
            
            # Calculate percentage difference
            diff = abs((val - ref) / ref)
            
            if diff <= threshold:
                current_cluster.append(val)
            else:
                clusters.append(current_cluster)
                current_cluster = [val]
        clusters.append(current_cluster)
    
    # Build a list of new amounts matching the sorted order
    new_amounts = []
    for cluster in clusters:
        mean_val = np.mean(cluster)
        new_amounts.extend([mean_val] * len(cluster))
        
    sorted_group['Amount'] = new_amounts
    return sorted_group

def get_subscription_candidates(df, groupby=['Description']):
    subscription_candidates = df.groupby(groupby).agg({
        'Amount': ['count', 'sum', 'mean'],
        'Date': ['min', 'max']
    }).reset_index()
    
    # Flatten columns based on what groupby produced
    # Columns are: GroupKey(s)..., Amount-count, Amount-sum, Amount-mean, Date-min, Date-max
    if len(subscription_candidates.columns) == 7:
        # Grouped by ['Description', 'Amount']
        subscription_candidates.columns = ['Description', 'Amount', 'Transaction_Count', 'Total_Spent', 'Avg_Amount', 'First_Transaction', 'Last_Transaction']
        # 'Amount' is the grouping key (exact cluster value), 'Avg_Amount' is the calculated mean (identical). 
        # We can drop Avg_Amount.
        subscription_candidates = subscription_candidates.drop(columns=['Avg_Amount'])
    else:
        # Grouped by ['Description']
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

    # Cluster amounts within each Description group to isolate outliers
    if not df.empty:
        try:
            df = df.groupby('Description', group_keys=False).apply(cluster_amounts, threshold=args.threshold)
        except Exception as e:
            if args.debug:
                print(f"Error during amount clustering: {e}")

    subscription_candidates = get_subscription_candidates(df, groupby=['Description', 'Amount'])
    subscription_candidates['First_Transaction'] = pd.to_datetime(subscription_candidates['First_Transaction'])
    subscription_candidates['Last_Transaction'] = pd.to_datetime(subscription_candidates['Last_Transaction'])
    subscription_candidates['Total_Days'] = (subscription_candidates['Last_Transaction'] - subscription_candidates['First_Transaction']).dt.days
    subscription_candidates['Avg_Days_Between_Transactions'] = subscription_candidates['Total_Days'] / (subscription_candidates['Transaction_Count'] - 1)
    
    subscription_candidates = subscription_candidates[(subscription_candidates['Avg_Days_Between_Transactions'] > 25) & (subscription_candidates['Avg_Days_Between_Transactions'] < 35)]
    
    subscription_candidates = subscription_candidates[
        (subscription_candidates['Amount'] < -args.min_transaction_amount) & 
        (subscription_candidates['Amount'] > -args.max_transaction_amount)
    ]
    
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