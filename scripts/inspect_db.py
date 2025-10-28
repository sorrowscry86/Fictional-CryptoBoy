"""Quick script to inspect database schema"""
import sqlite3
import pandas as pd

conn = sqlite3.connect('tradesv3.dryrun.sqlite')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print("Tables:", tables)
print()

# Check if pairlocks table exists and has balance info
for table in tables:
    print(f"\n=== {table} ===")
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()
    print("Columns:", [col[1] for col in columns])
    
    # Sample data
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table} LIMIT 3", conn)
        print(f"Sample ({len(df)} rows):")
        print(df)
    except:
        print("No data")

conn.close()
