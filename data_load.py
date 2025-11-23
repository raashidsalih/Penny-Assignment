import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# 1. Configuration
# Database configuration loaded from environment variables
DB_CONFIG = {
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'dbname': os.getenv('DB_NAME')
}

# File Paths
INPUT_CSV_PATH = os.getenv('INPUT_CSV_PATH', 'default_input.csv')
CLEANED_CSV_OUTPUT = os.getenv('CLEANED_CSV_OUTPUT', 'default_cleaned.csv')
TABLE_NAME = os.getenv('TABLE_NAME', 'california_procurement') # Used as dynamic placeholder
TABLE_SCHEMA_SQL = 'sql/table_schema.sql'
CHAT_SCHEMA_SQL = 'sql/chat_schema.sql'


# 2. Utility Functions
def get_db_connection():
    """Creates a SQLAlchemy engine connection."""
    conn_str = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
    engine = create_engine(conn_str)
    return engine

def execute_sql_file(engine, file_path, table_name=None):
    """Reads and executes a SQL file, replacing a placeholder if needed."""
    try:
        with open(file_path, 'r') as f:
            sql_command = f.read()
        
        # Replace dynamic table name placeholder used in SQL files
        if table_name:
            sql_command = sql_command.replace('__TABLE_NAME__', table_name)
        
        with engine.connect() as connection:
            # SQLAlchemy's connection.execute can handle multiple statements separated by semicolons
            connection.execute(text(sql_command))
            connection.commit()
        print(f"Successfully executed SQL commands from {file_path}.")
    except FileNotFoundError:
        print(f"Error: SQL file not found at {file_path}.")
        raise
    except Exception as e:
        print(f"Error executing SQL from {file_path}: {e}")
        raise

def clean_currency(val):
    """Removes '$' and ',' and converts to float."""
    if pd.isna(val) or val == '':
        return None
    if isinstance(val, str):
        val = val.replace('$', '').replace(',', '')
    try:
        return float(val)
    except ValueError:
        return None


# 3. Main Pipeline
def run_pipeline():
    print("--- Starting ETL Pipeline ---")
    
    # Extract
    print(f"Reading data from {INPUT_CSV_PATH}...")
    try:
        df = pd.read_csv(INPUT_CSV_PATH)
        print(f"Successfully loaded {len(df)} rows.")
    except FileNotFoundError:
        print("Error: Input CSV file not found.")
        return

    # Transform
    print("Cleaning data...")
    
    # Normalize Column Names
    df.columns = df.columns.str.replace(' ', '_').str.replace('-', '_').str.lower()
    
    # Date Conversion
    print("Converting dates...")
    date_cols = ['creation_date', 'purchase_date']
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    # Currency Cleaning
    print("Cleaning currency fields...")
    price_cols = ['unit_price', 'total_price']
    for col in price_cols:
        df[col] = df[col].apply(clean_currency)

    # Type Enforcement
    if 'supplier_code' in df.columns:
        df['supplier_code'] = df['supplier_code'].astype(str).str.replace('.0', '', regex=False)

    text_cols = ['lpa_number', 'requisition_number', 'supplier_zip_code', 'calcard']
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str) 

    numeric_unspsc_cols = ['normalized_unspsc', 'class', 'family', 'segment', 'quantity']
    for col in numeric_unspsc_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce') 

    # Save Cleaned Data
    print(f"Saving cleaned data to {CLEANED_CSV_OUTPUT}...")
    df.to_csv(CLEANED_CSV_OUTPUT, index=False)

    # Create Table & Indexes
    print(f"Connecting to database and creating table schema '{TABLE_NAME}' with indexes...")
    engine = get_db_connection()
    execute_sql_file(engine, TABLE_SCHEMA_SQL, table_name=TABLE_NAME)

    # Load data to Postgres
    print("Uploading data to PostgreSQL...")
    
    try:
        df.to_sql(
            TABLE_NAME, 
            engine, 
            if_exists='append', 
            index=False, 
            chunksize=10000,
            method=None
        )
        print("Success! Data upload complete.")
        
    except Exception as e:
        print(f"An error occurred during upload: {e}")
        return

    # Call chat_schema.sql
    print("Executing post-load schema commands for chat system...")
    execute_sql_file(engine, CHAT_SCHEMA_SQL)

    # Verify
    print("--- Summary ---")
    with engine.connect() as connection:
        result = connection.execute(text(f"SELECT COUNT(*) FROM {TABLE_NAME}"))
        count = result.scalar()
        print(f"Total rows currently in database table '{TABLE_NAME}': {count}")

if __name__ == "__main__":
    run_pipeline()