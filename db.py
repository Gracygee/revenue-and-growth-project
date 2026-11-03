import pandas as pd
import sqlite3

conn = sqlite3.connect("olist.db")
files = {
    "olist_customers_dataset": "customers",
    "olist_orders_dataset": "orders",
    "olist_order_items_dataset": "order_items",
    "olist_order_payments_dataset": "payments"
}

for csv_file, table_name in files.items():
    # try .csv extension, if your files have no extension add it
    try:
        df = pd.read_csv(f"{csv_file}.csv")
    except:
        df = pd.read_csv(csv_file) # if Windows hides extension
    
    # clean column names
    df.columns = [c.strip() for c in df.columns]
    
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    print(f"Loaded {table_name}: {len(df)} rows from {csv_file}")

conn.close()
print("DONE - olist.db created with 4 tables")


