import pandas as pd
import numpy as np
from pymongo import MongoClient, ASCENDING
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# 1. Configuration
# MongoDB configuration loaded from environment variables
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'penny_db')

# File Paths
INPUT_CSV_PATH = os.getenv('INPUT_CSV_PATH', 'default_input.csv')
CLEANED_CSV_OUTPUT = os.getenv('CLEANED_CSV_OUTPUT', 'default_cleaned.csv')
COLLECTION_NAME = os.getenv('TABLE_NAME', 'california_procurement')


# 2. Utility Functions
def get_db_connection():
    """Creates a MongoDB client connection and returns the database."""
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    return client, db


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


def create_indexes(collection):
    """Create indexes for faster query resolution."""
    print("Creating indexes...")
    
    # Index 1: Filtering by Department and Date (Common analytical queries)
    collection.create_index([
        ("department_name", ASCENDING),
        ("purchase_date", ASCENDING)
    ], name="idx_dept_date")
    
    # Index 2: Searching by Supplier (Common lookup)
    collection.create_index([("supplier_name", ASCENDING)], name="idx_supplier_name")
    
    # Index 3: Filtering by Contract/LPA Number (Used for contract spend analysis)
    collection.create_index([("lpa_number", ASCENDING)], name="idx_lpa_num")
    
    # Index 4: Filtering/Grouping by Acquisition Type
    collection.create_index([("acquisition_type", ASCENDING)], name="idx_acq_type")
    
    # Index 5: Filtering/Grouping by Fiscal Year
    collection.create_index([("fiscal_year", ASCENDING)], name="idx_fiscal_year")
    
    print("Indexes created successfully.")


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

    # Connect to MongoDB
    print(f"Connecting to MongoDB and preparing collection '{COLLECTION_NAME}'...")
    client, db = get_db_connection()
    collection = db[COLLECTION_NAME]
    
    # Drop existing collection to start fresh
    print(f"Dropping existing collection '{COLLECTION_NAME}' if it exists...")
    collection.drop()
    
    # Convert DataFrame to list of dictionaries for MongoDB insertion
    print("Converting data for MongoDB...")
    
    # Handle date columns first by converting to Python datetime or None
    # This must be done before replace() to avoid NaT serialization issues
    def convert_timestamp(x):
        """Convert pandas Timestamp to Python datetime, handling NaT."""
        if pd.isna(x):
            return None
        if hasattr(x, 'to_pydatetime'):
            try:
                return x.to_pydatetime().replace(tzinfo=None)
            except:
                return None
        return None
    
    for col in date_cols:
        if col in df.columns:
            df[col] = df[col].apply(convert_timestamp)
    
    # Replace remaining NaN with None for MongoDB compatibility
    df = df.replace({np.nan: None})
    
    records = df.to_dict('records')
    
    # Load data to MongoDB
    print("Uploading data to MongoDB...")
    
    try:
        # Insert in batches
        batch_size = 10000
        total_records = len(records)
        
        for i in range(0, total_records, batch_size):
            batch = records[i:i + batch_size]
            collection.insert_many(batch)
            print(f"  Inserted {min(i + batch_size, total_records)}/{total_records} records...")
        
        print("Success! Data upload complete.")
        
    except Exception as e:
        print(f"An error occurred during upload: {e}")
        client.close()
        return

    # Create indexes for faster queries
    create_indexes(collection)

    # Verify
    print("--- Summary ---")
    count = collection.count_documents({})
    print(f"Total documents currently in MongoDB collection '{COLLECTION_NAME}': {count}")
    
    # Close connection
    client.close()
    print("MongoDB connection closed.")

if __name__ == "__main__":
    run_pipeline()
