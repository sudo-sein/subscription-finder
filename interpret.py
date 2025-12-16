from utils import clean_amount, translate_column_names, unify_column_names, standard_columns
import sys
import pandas as pd
import numpy as np

# Load the CSV file from first argument
file_path = sys.argv[1]

def find_data_start(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        for i, line in enumerate(file):
            line_lower = line.lower()
            if (any(kw in line_lower for kw in standard_columns['Date']) and
                any(kw in line_lower for kw in standard_columns['Description']) and
                any(kw in line_lower for kw in standard_columns['Amount'])):
                return i
    return None

def cluster_amounts(group, threshold=0.10):
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

def get_subscription_candidates(df, groupby=['Description', 'Amount']):
    subscription_candidates = df.groupby(groupby).agg({
        'Amount': ['count', 'sum'],
        'Date': ['min', 'max']
    }).reset_index()
    subscription_candidates.columns = ['Description', 'Amount', 'Transaction_Count', 'Total_Spent', 'First_Transaction', 'Last_Transaction']
    subscription_candidates = subscription_candidates[subscription_candidates['Transaction_Count'] > 1]
    return subscription_candidates


start_row = find_data_start(file_path)
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

    # Cluster amounts within each Description group to combine similar subscriptions
    if not df.empty:
        # print("Columns before clustering:", df.columns.tolist())
        try:
            df = df.groupby('Description', group_keys=False).apply(cluster_amounts)
        except Exception as e:
            print(f"Error during clustering: {e}")
            print("Columns:", df.columns.tolist())
            exit(1)

    subscription_candidates = get_subscription_candidates(df, groupby=['Description', 'Amount'])
    subscription_candidates['First_Transaction'] = pd.to_datetime(subscription_candidates['First_Transaction'])
    subscription_candidates['Last_Transaction'] = pd.to_datetime(subscription_candidates['Last_Transaction'])
    subscription_candidates['Total_Days'] = (subscription_candidates['Last_Transaction'] - subscription_candidates['First_Transaction']).dt.days
    subscription_candidates['Avg_Days_Between_Transactions'] = subscription_candidates['Total_Days'] / (subscription_candidates['Transaction_Count'] - 1)
    
    subscription_candidates = subscription_candidates[(subscription_candidates['Avg_Days_Between_Transactions'] > 25) & (subscription_candidates['Avg_Days_Between_Transactions'] < 35)]
    
    subscription_candidates = subscription_candidates[(subscription_candidates['Amount'] < -10) & (subscription_candidates['Amount'] > -1000)]
    
    # Calculate yearly cost
    subscription_candidates['Yearly_Cost'] = subscription_candidates['Amount'] * 12

    print("Number of potential subscriptions:", len(subscription_candidates))
    
    # Display potential subscriptions
    print(subscription_candidates[['Description', 'Amount', 'Yearly_Cost', 'Last_Transaction', 'Transaction_Count']].sort_values('Yearly_Cost', ascending=True))
else:
    print("Dataframe is empty.")
# print(df.head())