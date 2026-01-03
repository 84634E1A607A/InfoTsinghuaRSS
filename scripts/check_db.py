#!/usr/bin/env python3
"""Check database schema."""

import sqlite3

db_path = "info_rss.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("Tables in database:")
for table in tables:
    print(f"  - {table[0]}")
    # Get schema (safe: table names are from sqlite_master, not user input)
    cursor.execute("PRAGMA table_info(?)", (table[0],))
    columns = cursor.fetchall()
    print(f"    Columns:")
    for col in columns:
        print(f"      {col[1]} ({col[2]})")
    print()

conn.close()
