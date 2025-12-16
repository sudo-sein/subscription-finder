# Subscription Finder Python Script

This Python script is designed to help users find and manage their subscriptions.

## Setup

To set up the project, follow these steps:

1. **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-name>
    ```

2. **Create a virtual environment:** 
   
   Windows CMD:
    ```cmd
    python -m venv venv
    venv\Scripts\activate
    ```

    Bash:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
    
3. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

To use the script, run the following command:

```bash
python interpret.py <path_to_csv_file> [options]
```

**Example:**
```bash
python interpret.py reports/financial_reports.csv --recency-days 120 --threshold 0.2
```

### Command-line Arguments

| Argument | Short | Default | Description |
| :--- | :--- | :--- | :--- |
| `file_path` | | | Path to the CSV file to analyze (Required). |
| `--threshold` | `-t` | `0.15` | Percentage threshold (0.0-1.0) for clustering similar transaction amounts. |
| `--recency-days` | `-r` | `90` | Number of days from the latest transaction date to consider a subscription "active". |
| `--min-transaction-amount` | | `10.0` | Minimum absolute transaction amount to consider. |
| `--max-transaction-amount` | | `10000.0` | Maximum absolute transaction amount to consider. |
| `--ignore-file` | | `ignore_subscriptions.txt` | Path to a text file containing vendor names to ignore. |
| `--debug` | `-d` | `False` | Enable verbose debug output. |

### Ignoring Vendors

You can exclude specific vendors or transactions by adding their names to a text file (default: `ignore_subscriptions.txt`).
- One vendor per line.
- Supports partial matching (e.g., "Grocery" will ignore "Joe's Grocery Store").
- Case-insensitive.

Example `ignore_subscriptions.txt`:
```text
Whole Foods
Starbucks
One-time transfer
```

## How It Works

1. **Parses & Normalizes:** Reads the CSV, detects column names automatically (multilingual support), and normalizes vendor descriptions (removes location data, special characters, etc.).
2. **Fuzzy Matching:** Groups similar vendor names together (e.g., "Netflix.com" and "Netflix Inc") using sequence matching logic.
3. **Ignores:** Filters out vendors listed in the ignore file.
4. **Clusters Amounts:** Groups transactions from the same vendor that have similar amounts (within the specified `--threshold`) to handle small price variations or currency fluctuations. This also helps separate recurring payments from one-off outliers (like a large downpayment vs. a monthly fee).
5. **Identifies Candidates:** Filters for recurring transactions (count > 1) that fall within the specified amount range and recency window.
6. **Reports:** specific details about the potential subscriptions found, sorted by estimated yearly cost.
