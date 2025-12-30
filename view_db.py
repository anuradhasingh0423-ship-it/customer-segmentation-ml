import sqlite3
import pandas as pd

conn = sqlite3.connect("customer_segments.db")
df = pd.read_sql("""
SELECT cluster, COUNT(*) as count
FROM predictions
GROUP BY cluster
""", conn)
conn.close()

print(df)
