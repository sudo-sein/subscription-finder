from utils import clean_amount, translate_column_names, unify_column_names, standard_columns
import sys
import pandas as pd

# Load the CSV file from first argument
file_path = sys.argv[1]

def find_data_start(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        for i, line in enumerate(file):
            if 'Data' in line and 'Opis' in line and 'Kwota' in line:
                return i
            if 'Date' in line and 'Description' in line and 'Amount' in line:
                return i
    return None

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
    df = pd.read_csv(file_path, skiprows=start_row, sep=';', index_col=False,)
else:
    print("No valid data header found in the file.")
    
# Example: Translate column names
if not df.empty:
    df.columns = translate_column_names(df.columns, src_lang='pl')
    df = unify_column_names(df, standard_columns)

    # Example: Convert 'Date' column to datetime
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    df['Amount'] = pd.to_numeric(df['Amount'].apply(clean_amount), errors='coerce')

    # Example: Handle missing values
    df.dropna(subset=['Description', 'Amount'], inplace=True)


    subscription_candidates = get_subscription_candidates(df, groupby=['Description', 'Amount'])
    subscription_candidates['First_Transaction'] = pd.to_datetime(subscription_candidates['First_Transaction'])
    subscription_candidates['Last_Transaction'] = pd.to_datetime(subscription_candidates['Last_Transaction'])
    subscription_candidates['Total_Days'] = (subscription_candidates['Last_Transaction'] - subscription_candidates['First_Transaction']).dt.days
    subscription_candidates['Avg_Days_Between_Transactions'] = subscription_candidates['Total_Days'] / (subscription_candidates['Transaction_Count'] - 1)
    
    subscription_candidates = subscription_candidates[(subscription_candidates['Avg_Days_Between_Transactions'] > 25) & (subscription_candidates['Avg_Days_Between_Transactions'] < 35)]
    
    subscription_candidates = subscription_candidates[(subscription_candidates['Amount'] < -10) & (subscription_candidates['Amount'] > -1000)]
    
    print("Number of potential subscriptions:", len(subscription_candidates))
    
    # Display potential subscriptions
    print(subscription_candidates[['Description', 'Amount', 'Last_Transaction', 'Transaction_Count']].sort_values('Last_Transaction', ascending=False))
else:
    print("Dataframe is empty.")
# print(df.head())

def find_data_start(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        for i, line in enumerate(file):
            if 'Data' in line and 'Opis' in line and 'Kwota' in line:
                return i
            if 'Date' in line and 'Description' in line and 'Amount' in line:
                return i
    return None

def get_subscription_candidates(df, groupby=['Description']):
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
    df = pd.read_csv(file_path, skiprows=start_row, sep=';', index_col=False,)
else:
    print("No valid data header found in the file.")
    
# Example: Translate column names
if not df.empty:
    df.columns = translate_column_names(df.columns, src_lang='pl')
    df = unify_column_names(df, standard_columns)

    # Example: Convert 'Date' column to datetime
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    df['Amount'] = pd.to_numeric(df['Amount'].apply(clean_amount), errors='coerce')

    # Example: Handle missing values
    df.dropna(subset=['Description', 'Amount'], inplace=True)


    subscription_candidates = get_subscription_candidates(df, groupby=['Description', 'Amount'])
    subscription_candidates['First_Transaction'] = pd.to_datetime(subscription_candidates['First_Transaction'])
    subscription_candidates['Last_Transaction'] = pd.to_datetime(subscription_candidates['Last_Transaction'])
    subscription_candidates['Total_Days'] = (subscription_candidates['Last_Transaction'] - subscription_candidates['First_Transaction']).dt.days
    subscription_candidates['Avg_Days_Between_Transactions'] = subscription_candidates['Total_Days'] / (subscription_candidates['Transaction_Count'] - 1)
    
    subscription_candidates = subscription_candidates[(subscription_candidates['Avg_Days_Between_Transactions'] > 25) & (subscription_candidates['Avg_Days_Between_Transactions'] < 35)]
    
    subscription_candidates = subscription_candidates[(subscription_candidates['Amount'] < -10) & (subscription_candidates['Amount'] > -1000)]
    
    print("Number of potential subscriptions:", len(subscription_candidates))
    
    # Display potential subscriptions
    print(subscription_candidates[['Description', 'Amount', 'Transaction_Count', 'Total_Spent', 'Last_Transaction']].sort_values('Last_Transaction', ascending=False))
else:
    print("Dataframe is empty.")
# print(df.head())
