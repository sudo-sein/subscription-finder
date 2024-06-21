from deep_translator import GoogleTranslator
import re

standard_columns = {
    'Date': ['date', 'datum', 'fecha', 'data'],
    'Description': ['description', 'desc', 'descripción', 'bezeichnung', 'opis'],
    'Amount': ['amount', 'amt', 'importe', 'betrag', 'kwota', 'sum'],
    # 'Category': ['category', 'kategorie', 'categoría', 'kategorie', 'kategoria'],
    # Add other standard columns and their variations
}
def translate_column_names(columns, src_lang, dest_lang='en'):
    translated_columns = []
    for col in columns:
        try:
            translated = GoogleTranslator(source=src_lang, target=dest_lang).translate(col)
            translated_columns.append(translated)
        except Exception as e:
            print(f"Error translating column '{col}': {e}")
            translated_columns.append(col)  # Use the original column name if translation fails
    return translated_columns

def escape_special_chars(text):
    return re.escape(text)

def clean_amount(amount):
    # Remove currency symbols and any non-numeric characters except for the minus sign and comma
    amount = re.sub(r'[^\d,-]', '', amount)
    # Replace comma with dot
    amount = amount.replace(',', '.')
    return amount

def map_columns_with_prefix_suffix(columns, standard_columns):
    column_mapping = {}
    for col in columns:
        standardized_col = None
        for standard, variations in standard_columns.items():
            for var in variations:
                # Escape special characters in the variation
                escaped_var = escape_special_chars(var)
                # Updated pattern to avoid issues with special characters and unbalanced parentheses
                pattern = rf'\b{escaped_var}\b'
                if re.search(pattern, col, re.IGNORECASE):
                    standardized_col = standard
                    break
            if standardized_col:
                break
        if standardized_col:
            column_mapping[col] = standardized_col
        else:
            column_mapping[col] = col  # Keep original if no match found
    return column_mapping

def unify_column_names(df, standard_columns):
    column_mapping = map_columns_with_prefix_suffix(df.columns, standard_columns)
    df.rename(columns=column_mapping, inplace=True)
    return df