# export_db.py
import sqlite3

# Path to your SQLite DB
conn = sqlite3.connect("db.sqlite3")

with open("db_export.sql", "w", encoding="utf-8") as f:
    for line in conn.iterdump():
        f.write(f"{line}\n")

conn.close()
print("Database exported successfully to db_export.sql")
